from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from apps.api.app.database.session import get_db
from apps.api.app.core.security import encrypt_secret, decrypt_secret
from apps.api.app.core.dependencies import get_current_user, require_role
from apps.api.app.models.entities import (
    Project,
    ProjectSource,
    EnvironmentVariable,
    Server,
    Deployment,
    Container,
    User,
)
from apps.api.app.schemas.all_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    EnvironmentUpdateRequest,
    EnvironmentItemResponse,
    DeploymentResponse,
    ContainerResponse,
)
from apps.api.app.services.audit_service import log_activity

router = APIRouter(prefix="/projects", tags=["Project Management"])

def mask_secret(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 4:
        return "****"
    return val[:2] + "****" + val[-2:]

@router.get("", response_model=List[ProjectResponse])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        src = p.source
        result.append(
            ProjectResponse(
                id=p.id,
                server_id=p.server_id,
                server_name=p.server.name if p.server else "Unknown Server",
                owner_id=p.owner_id,
                name=p.name,
                description=p.description,
                framework=p.framework,
                source_type=p.source_type,
                status=p.status,
                repository_url=src.repository_url if src else None,
                branch=src.branch if src else None,
                dockerfile_path=src.dockerfile_path if src else None,
                compose_path=src.compose_path if src else None,
                created_at=p.created_at
            )
        )
    return result

@router.post("", response_model=ProjectResponse)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == payload.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Target server not found")

    project = Project(
        server_id=payload.server_id,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        framework=payload.framework,
        source_type=payload.source_type,
        status="active"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create project source config
    source = ProjectSource(
        project_id=project.id,
        repository_url=payload.repository_url,
        branch=payload.branch or "main",
        dockerfile_path=payload.dockerfile_path or "Dockerfile",
        compose_path=payload.compose_path or "docker-compose.yml"
    )
    db.add(source)
    db.commit()

    log_activity(
        db,
        action="project.create",
        resource_type="project",
        resource_id=project.id,
        user_id=current_user.id,
        details={"name": project.name, "source_type": project.source_type}
    )

    return ProjectResponse(
        id=project.id,
        server_id=project.server_id,
        server_name=server.name,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        framework=project.framework,
        source_type=project.source_type,
        status=project.status,
        repository_url=source.repository_url,
        branch=source.branch,
        dockerfile_path=source.dockerfile_path,
        compose_path=source.compose_path,
        created_at=project.created_at
    )

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    src = p.source
    return ProjectResponse(
        id=p.id,
        server_id=p.server_id,
        server_name=p.server.name if p.server else "Unknown Server",
        owner_id=p.owner_id,
        name=p.name,
        description=p.description,
        framework=p.framework,
        source_type=p.source_type,
        status=p.status,
        repository_url=src.repository_url if src else None,
        branch=src.branch if src else None,
        dockerfile_path=src.dockerfile_path if src else None,
        compose_path=src.compose_path if src else None,
        created_at=p.created_at
    )

@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.name is not None:
        p.name = payload.name
    if payload.description is not None:
        p.description = payload.description
    if payload.framework is not None:
        p.framework = payload.framework

    src = p.source
    if src:
        if payload.repository_url is not None:
            src.repository_url = payload.repository_url
        if payload.branch is not None:
            src.branch = payload.branch
        if payload.dockerfile_path is not None:
            src.dockerfile_path = payload.dockerfile_path
        if payload.compose_path is not None:
            src.compose_path = payload.compose_path

    db.commit()
    db.refresh(p)

    log_activity(
        db,
        action="project.update",
        resource_type="project",
        resource_id=p.id,
        user_id=current_user.id
    )
    return get_project(project_id=project_id, current_user=current_user, db=db)

@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(p)
    db.commit()

    log_activity(
        db,
        action="project.delete",
        resource_type="project",
        resource_id=project_id,
        user_id=current_user.id
    )
    return {"message": "Project deleted successfully"}

@router.get("/{project_id}/environment", response_model=List[EnvironmentItemResponse])
def get_project_environment(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    items = db.query(EnvironmentVariable).filter(EnvironmentVariable.project_id == project_id).all()
    results = []
    for item in items:
        # Decrypt to mask securely
        try:
            val = decrypt_secret(item.encrypted_value)
            masked = mask_secret(val)
        except Exception:
            masked = "********"
        results.append(
            EnvironmentItemResponse(
                key=item.key,
                masked_value=masked,
                updated_at=item.updated_at
            )
        )
    return results

@router.put("/{project_id}/environment")
def update_project_environment(
    project_id: str,
    payload: EnvironmentUpdateRequest,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    # Replace variables with encrypted values
    db.query(EnvironmentVariable).filter(EnvironmentVariable.project_id == project_id).delete()

    for item in payload.variables:
        encrypted = encrypt_secret(item.value)
        db_var = EnvironmentVariable(
            project_id=project_id,
            key=item.key.strip(),
            encrypted_value=encrypted
        )
        db.add(db_var)

    db.commit()

    log_activity(
        db,
        action="project.environment_update",
        resource_type="project",
        resource_id=project_id,
        user_id=current_user.id,
        details={"keys_updated": [i.key for i in payload.variables]}
    )
    return {"message": "Environment variables encrypted and updated"}

@router.get("/{project_id}/deployments", response_model=List[DeploymentResponse])
def get_project_deployments(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deployments = db.query(Deployment).filter(
        Deployment.project_id == project_id
    ).order_by(Deployment.created_at.desc()).all()
    return deployments
