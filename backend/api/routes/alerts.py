"""
Alert Routes – list alerts.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User
from backend.models.alert import Alert
from backend.schemas.response_schema import AlertResponse

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all alerts, newest first."""
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    return [AlertResponse.model_validate(a) for a in alerts]
