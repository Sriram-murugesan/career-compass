"""Auth module — public interface. Other modules import only from here:

from app.modules.auth import CurrentUserId
"""

from app.modules.auth.dependencies import CurrentUserId
from app.modules.auth.router import router

__all__ = ["CurrentUserId", "router"]
