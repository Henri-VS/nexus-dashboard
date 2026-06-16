from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class CertTracker(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    exam_date: Optional[date] = None
    status: str = "studying"  # studying | scheduled | passed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
