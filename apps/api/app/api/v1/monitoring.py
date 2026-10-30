from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from apps.api.app.database.session import get_db
from apps.api.app.core.dependencies import get_current_user
from apps.api.app.models.entities import Server, Container, ServerMetric, Deployment, User
from apps.api.app.api.v1.servers import compute_server_status

router = APIRouter(prefix="/monitoring", tags=["Monitoring Center"])

@router.get("/overview")
def get_monitoring_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    servers = db.query(Server).all()
    total_servers = len(servers)
    online_count = 0
    offline_count = 0
    degraded_count = 0

    cpu_sum = 0.0
    mem_sum = 0.0
    disk_sum = 0.0
    active_metrics_count = 0

    alerts = []

    for s in servers:
        st = compute_server_status(s)
        if st == "online":
            online_count += 1
        elif st == "offline":
            offline_count += 1
            alerts.append({
                "id": f"alert-offline-{s.id}",
                "level": "warning",
                "title": f"Server {s.name} is offline",
                "description": f"No heartbeat received in the last 45 seconds",
                "server_id": s.id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        elif st == "degraded":
            degraded_count += 1

        # Check latest metric
        latest_metric = db.query(ServerMetric).filter(
            ServerMetric.server_id == s.id
        ).order_by(ServerMetric.recorded_at.desc()).first()

        if latest_metric:
            cpu_sum += latest_metric.cpu_usage
            mem_sum += latest_metric.memory_usage
            disk_sum += latest_metric.disk_usage
            active_metrics_count += 1

            if latest_metric.cpu_usage > 90.0:
                alerts.append({
                    "id": f"alert-cpu-{s.id}",
                    "level": "critical",
                    "title": f"High CPU usage on {s.name}",
                    "description": f"CPU usage exceeded 90% ({latest_metric.cpu_usage:.1f}%)",
                    "server_id": s.id,
                    "timestamp": latest_metric.recorded_at.isoformat()
                })
            if latest_metric.memory_usage > 90.0:
                alerts.append({
                    "id": f"alert-mem-{s.id}",
                    "level": "critical",
                    "title": f"High Memory usage on {s.name}",
                    "description": f"Memory usage exceeded 90% ({latest_metric.memory_usage:.1f}%)",
                    "server_id": s.id,
                    "timestamp": latest_metric.recorded_at.isoformat()
                })

    avg_cpu = (cpu_sum / active_metrics_count) if active_metrics_count > 0 else 0.0
    avg_mem = (mem_sum / active_metrics_count) if active_metrics_count > 0 else 0.0
    avg_disk = (disk_sum / active_metrics_count) if active_metrics_count > 0 else 0.0

    total_containers = db.query(Container).count()
    running_containers = db.query(Container).filter(Container.status == "running").count()

    recent_deployments = db.query(Deployment).order_by(
        Deployment.created_at.desc()
    ).limit(5).all()

    return {
        "servers": {
            "total": total_servers,
            "online": online_count,
            "offline": offline_count,
            "degraded": degraded_count,
        },
        "resources": {
            "avg_cpu_percent": round(avg_cpu, 1),
            "avg_memory_percent": round(avg_mem, 1),
            "avg_disk_percent": round(avg_disk, 1),
        },
        "containers": {
            "total": total_containers,
            "running": running_containers,
            "stopped": total_containers - running_containers
        },
        "recent_deployments_count": len(recent_deployments),
        "alerts": alerts
    }

@router.get("/alerts")
def get_active_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    overview = get_monitoring_overview(current_user=current_user, db=db)
    return overview.get("alerts", [])

@router.get("/history")
def get_historical_metrics(
    server_id: Optional[str] = None,
    range_hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ServerMetric)
    if server_id:
        query = query.filter(ServerMetric.server_id == server_id)
        
    since = datetime.now(timezone.utc) - timedelta(hours=range_hours)
    query = query.filter(ServerMetric.recorded_at >= since).order_by(ServerMetric.recorded_at.asc())
    records = query.all()

    return [
        {
            "server_id": r.server_id,
            "cpu": r.cpu_usage,
            "memory": r.memory_usage,
            "disk": r.disk_usage,
            "network_rx": r.network_rx,
            "network_tx": r.network_tx,
            "time": r.recorded_at.strftime("%H:%M")
        }
        for r in records
    ]
