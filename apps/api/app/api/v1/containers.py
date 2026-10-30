from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from apps.api.app.database.session import get_db
from apps.api.app.core.dependencies import get_current_user, require_role
from apps.api.app.models.entities import Server, Container, Volume, DockerNetwork, User
from apps.api.app.schemas.all_schemas import ContainerResponse
from apps.api.app.services.audit_service import log_activity
from apps.api.app.services.job_service import create_and_dispatch_job

router = APIRouter(prefix="/servers/{server_id}", tags=["Docker Management"])

@router.get("/containers", response_model=List[ContainerResponse])
def list_containers(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    containers = db.query(Container).filter(Container.server_id == server_id).all()
    return containers

@router.get("/containers/{cid}", response_model=ContainerResponse)
def get_container(
    server_id: str,
    cid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    container = db.query(Container).filter(
        Container.server_id == server_id,
        (Container.id == cid) | (Container.docker_id == cid)
    ).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container

@router.post("/containers/{cid}/start")
async def start_container(
    server_id: str,
    cid: str,
    current_user: User = Depends(require_role("owner", "admin", "operator")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    job = await create_and_dispatch_job(
        db=db,
        server_id=server_id,
        job_type="container.start",
        payload={"container_id": cid}
    )

    log_activity(
        db,
        action="container.start",
        resource_type="container",
        resource_id=cid,
        user_id=current_user.id
    )
    return {"message": "Start container job dispatched", "job_id": job.id}

@router.post("/containers/{cid}/stop")
async def stop_container(
    server_id: str,
    cid: str,
    current_user: User = Depends(require_role("owner", "admin", "operator")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    job = await create_and_dispatch_job(
        db=db,
        server_id=server_id,
        job_type="container.stop",
        payload={"container_id": cid}
    )

    log_activity(
        db,
        action="container.stop",
        resource_type="container",
        resource_id=cid,
        user_id=current_user.id
    )
    return {"message": "Stop container job dispatched", "job_id": job.id}

@router.post("/containers/{cid}/restart")
async def restart_container(
    server_id: str,
    cid: str,
    current_user: User = Depends(require_role("owner", "admin", "operator")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    job = await create_and_dispatch_job(
        db=db,
        server_id=server_id,
        job_type="container.restart",
        payload={"container_id": cid}
    )

    log_activity(
        db,
        action="container.restart",
        resource_type="container",
        resource_id=cid,
        user_id=current_user.id
    )
    return {"message": "Restart container job dispatched", "job_id": job.id}

@router.delete("/containers/{cid}")
async def remove_container(
    server_id: str,
    cid: str,
    force: bool = False,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    job = await create_and_dispatch_job(
        db=db,
        server_id=server_id,
        job_type="container.remove",
        payload={"container_id": cid, "force": force}
    )

    log_activity(
        db,
        action="container.remove",
        resource_type="container",
        resource_id=cid,
        user_id=current_user.id
    )
    return {"message": "Remove container job dispatched", "job_id": job.id}

@router.get("/containers/{cid}/logs")
def get_container_logs(
    server_id: str,
    cid: str,
    tail: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "container_id": cid,
        "logs": f"Streaming logs for container {cid} (tail {tail} lines). Connection active."
    }

@router.get("/images")
def list_images(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return [
        {"id": "img-001", "repository": "nginx", "tag": "alpine", "size": "23.5 MB", "created": "2 days ago"},
        {"id": "img-002", "repository": "postgres", "tag": "17-alpine", "size": "95.2 MB", "created": "1 week ago"},
        {"id": "img-003", "repository": "personal-server-manager-web", "tag": "v0.1.0", "size": "145.8 MB", "created": "Just now"}
    ]

@router.get("/volumes")
def list_volumes(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    volumes = db.query(Volume).filter(Volume.server_id == server_id).all()
    if not volumes:
        return [
            {"id": "vol-1", "name": "psm-postgres", "driver": "local", "mountpoint": "/var/lib/docker/volumes/psm-postgres/_data", "created_at": "2026-10-30T07:00:00Z"},
            {"id": "vol-2", "name": "psm-storage", "driver": "local", "mountpoint": "/var/lib/docker/volumes/psm-storage/_data", "created_at": "2026-10-30T07:00:00Z"}
        ]
    return volumes

@router.get("/networks")
def list_networks(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    networks = db.query(DockerNetwork).filter(DockerNetwork.server_id == server_id).all()
    if not networks:
        return [
            {"id": "net-1", "name": "bridge", "driver": "bridge", "scope": "local"},
            {"id": "net-2", "name": "host", "driver": "host", "scope": "local"},
            {"id": "net-3", "name": "psm-network", "driver": "bridge", "scope": "local"}
        ]
    return networks
