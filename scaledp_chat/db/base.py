from sqlalchemy.orm import DeclarativeBase

from scaledp_chat.db.meta import meta


class Base(DeclarativeBase):
    """Base for all models."""

    metadata = meta
