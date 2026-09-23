from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now - SQLModel's DateTime column now rejects naive
    datetimes, so every model's default_factory needs this instead of the
    naive datetime.utcnow()."""
    return datetime.now(timezone.utc)
