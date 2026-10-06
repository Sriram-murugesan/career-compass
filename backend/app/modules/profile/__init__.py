"""Profile module — public interface."""

from app.modules.profile.dependencies import profile_service_for
from app.modules.profile.router import router
from app.modules.profile.service import ProfileService

__all__ = ["ProfileService", "profile_service_for", "router"]
