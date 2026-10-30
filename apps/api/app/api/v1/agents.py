import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Header
from sqlalchemy.orm import Session
from apps.api.app.database.session import get_db, SessionLocal
from apps.api.app.core.security import hash_token
from apps.api.app.core.dependencies import get_current_agent
from apps.api.app.models.entities import (
    Server,
    Agent,
    AgentToken,
    ServerMetric,
    Job,
    DeploymentLog,
)
from apps.api.app.schemas.all_schemas import (
    AgentRegisterRequest,
    HeartbeatRequest,
    MetricsReportRequest,
    JobCompleteRequest,
    JobLogBatchRequest,
    JobResponse,
)
from apps.api.app.services.job_service import claim_next_job, complete_job
from apps.api.app.websocket.manager import ws_manager

router = APIRouter(prefix="/agents", tags=["Agent"])

@router.post("/register")
def register_agent(payload: AgentRegisterRequest, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == payload.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    token_hash = hash_token(payload.agent_token)
    token_record = db.query(AgentToken).filter(
        AgentToken.server_id == payload.server_id,
        AgentToken.token_hash == token_hash
    ).first()

    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid registration token")

    now = datetime.now(timezone.utc)
    # Create or update agent
    agent = db.query(Agent).filter(Agent.server_id == payload.server_id).first()
    if not agent:
        agent = Agent(
            server_id=payload.server_id,
            agent_version=payload.agent_version,
            credential_hash=token_hash,
            connected_at=now,
            last_seen=now
        )
        db.add(agent)
    else:
        agent.agent_version = payload.agent_version
        agent.credential_hash = token_hash
        agent.connected_at = now
        agent.last_seen = now
        agent.revoked_at = None

    # Update server details if reported by agent
    if payload.os_name:
        server.os_name = payload.os_name
    if payload.os_version:
        server.os_version = payload.os_version
    if payload.architecture:
        server.architecture = payload.architecture
    if payload.hostname:
        server.hostname = payload.hostname

    server.status = "online"
    server.last_seen = now
    db.commit()

    return {
        "status": "registered",
        "server_id": server.id,
        "agent_id": agent.id,
        "message": "Agent registered successfully"
    }

@router.post("/heartbeat")
def agent_heartbeat(payload: HeartbeatRequest, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == payload.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    now = datetime.now(timezone.utc)
    server.last_seen = now
    server.status = "online" if payload.status == "online" else "degraded"

    if server.agent:
        server.agent.last_seen = now
        server.agent.agent_version = payload.agent_version

    db.commit()
    return {"status": "ok", "server_id": server.id}

@router.post("/metrics")
async def report_metrics(payload: MetricsReportRequest, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == payload.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    now = datetime.now(timezone.utc)
    server.last_seen = now
    server.status = "online"

    metric = ServerMetric(
        server_id=server.id,
        cpu_usage=payload.cpu_usage,
        memory_usage=payload.memory_usage,
        memory_used_bytes=payload.memory_used_bytes,
        memory_total_bytes=payload.memory_total_bytes,
        disk_usage=payload.disk_usage,
        disk_used_bytes=payload.disk_used_bytes,
        disk_total_bytes=payload.disk_total_bytes,
        network_rx=payload.network_rx_bytes_per_sec,
        network_tx=payload.network_tx_bytes_per_sec,
        uptime=payload.uptime_seconds,
        recorded_at=now
    )
    db.add(metric)
    db.commit()

    # Broadcast to WebSocket listeners
    event_data = {
        "event": "server.metrics.updated",
        "server_id": server.id,
        "data": {
            "cpu_usage": payload.cpu_usage,
            "memory_usage": payload.memory_usage,
            "memory_used_bytes": payload.memory_used_bytes,
            "memory_total_bytes": payload.memory_total_bytes,
            "disk_usage": payload.disk_usage,
            "disk_used_bytes": payload.disk_used_bytes,
            "disk_total_bytes": payload.disk_total_bytes,
            "network_rx": payload.network_rx_bytes_per_sec,
            "network_tx": payload.network_tx_bytes_per_sec,
            "uptime": payload.uptime_seconds,
            "recorded_at": now.isoformat()
        }
    }
    await ws_manager.broadcast_server_event(server.id, event_data)

    return {"status": "recorded"}

@router.post("/jobs/claim")
def claim_job(server: Server = Depends(get_current_agent), db: Session = Depends(get_db)):
    job = claim_next_job(db=db, server_id=server.id)
    if not job:
        return {"job": None}
    return {"job": JobResponse.model_validate(job)}

@router.post("/jobs/{job_id}/complete")
def finish_job(
    job_id: str,
    payload: JobCompleteRequest,
    server: Server = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    job = complete_job(
        db=db,
        job_id=job_id,
        status=payload.status,
        output=payload.output,
        error_message=payload.error_message,
        duration_seconds=payload.duration_seconds
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "ok", "job_id": job.id}

@router.post("/jobs/{job_id}/logs")
async def receive_job_logs(
    job_id: str,
    payload: JobLogBatchRequest,
    server: Server = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id, Job.server_id == server.id).first()
    if not job or not job.deployment_id:
        return {"status": "skipped_no_deployment"}

    now = datetime.now(timezone.utc)
    for item in payload.logs:
        log_record = DeploymentLog(
            deployment_id=job.deployment_id,
            sequence=item.get("sequence", 0),
            level=item.get("level", "info"),
            message=item.get("message", ""),
            created_at=now
        )
        db.add(log_record)

        # Broadcast realtime log to browser clients watching this deployment
        await ws_manager.broadcast_deployment_log(
            job.deployment_id,
            {
                "deployment_id": job.deployment_id,
                "sequence": item.get("sequence", 0),
                "level": item.get("level", "info"),
                "message": item.get("message", ""),
                "created_at": now.isoformat()
            }
        )

    db.commit()
    return {"status": "logs_stored", "count": len(payload.logs)}

# --- Persistent Agent WebSocket Connection ---
@router.websocket("/connect")
async def agent_websocket_connect(websocket: WebSocket):
    # Query parameters: server_id, token
    server_id = websocket.query_params.get("server_id")
    token = websocket.query_params.get("token")

    if not server_id or not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()
    try:
        token_hash = hash_token(token)
        server = db.query(Server).filter(Server.id == server_id).first()
        valid = False
        if server and server.agent and server.agent.credential_hash == token_hash and not server.agent.revoked_at:
            valid = True
        elif server:
            tok = db.query(AgentToken).filter(AgentToken.server_id == server_id, AgentToken.token_hash == token_hash).first()
            if tok:
                valid = True

        if not valid:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Register connection
        await ws_manager.register_agent(server_id, websocket)
        server.status = "online"
        server.last_seen = datetime.now(timezone.utc)
        db.commit()

        # Listen for messages/pings from agent
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                msg_type = data.get("type")
                if msg_type == "heartbeat":
                    server.last_seen = datetime.now(timezone.utc)
                    db.commit()
                    await websocket.send_text(json.dumps({"type": "heartbeat_ack"}))
            except Exception:
                pass

    except WebSocketDisconnect:
        ws_manager.unregister_agent(server_id, websocket)
    finally:
        db.close()
