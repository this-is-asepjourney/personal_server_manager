from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from apps.api.app.database.session import get_db
from apps.api.app.core.dependencies import get_current_user, require_role
from apps.api.app.models.entities import AuditLog, User
from apps.api.app.schemas.all_schemas import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(50, le=200),
    offset: int = 0,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    results = []
    for log in logs:
        results.append(
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_name=log.user.name if log.user else "System",
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )
    return results
