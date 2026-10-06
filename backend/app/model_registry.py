"""Imports every module's models so Base.metadata knows all tables.

Used by Alembic (autogenerate) and tests. When you add a module with tables,
add one import line here.
"""

from app.db.base import Base
from app.memory import models as memory_models
from app.modules.auth import models as auth_models
from app.modules.chat import models as chat_models
from app.modules.profile import models as profile_models

__all__ = ["Base", "auth_models", "chat_models", "memory_models", "profile_models"]
