from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CalendarEvent(SQLModel, table=True):
    __tablename__ = "calendar_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    date: str        # "YYYY-MM-DD"
    time: str = ""   # "HH:MM" or ""
    description: str = ""
    repeat: str = "none"   # none | daily | weekly | monthly
    notify: bool = False
    color: str = "#7c8cf8"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
