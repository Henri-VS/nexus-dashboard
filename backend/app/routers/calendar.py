import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import engine, get_session
from app.models.calendar import CalendarEvent
from app.routers.notifications import send_notification, _load_config as _notif_cfg

router = APIRouter()


class EventIn(BaseModel):
    title: str
    date: str
    time: str = ""
    description: str = ""
    repeat: str = "none"
    notify: bool = False
    color: str = "#7c8cf8"


@router.get("/events")
async def list_events(session: Session = Depends(get_session)):
    return [e.model_dump() for e in session.exec(select(CalendarEvent)).all()]


@router.post("/events", status_code=201)
async def create_event(body: EventIn, session: Session = Depends(get_session)):
    ev = CalendarEvent(**body.model_dump())
    session.add(ev)
    session.commit()
    session.refresh(ev)
    if body.notify:
        suffix = f" at {body.time}" if body.time else ""
        await send_notification(
            title=body.title,
            message=f"{body.title}{suffix} on {body.date}",
            feature="calendar",
            event="create",
            tags="calendar",
        )
    return ev.model_dump()


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: int, session: Session = Depends(get_session)):
    ev = session.get(CalendarEvent, event_id)
    if ev:
        session.delete(ev)
        session.commit()


_REMINDER_MINUTES = {"5m": 5, "15m": 15, "30m": 30, "1h": 60}


async def reminder_loop() -> None:
    """Send reminders for upcoming events. Fires every 60 s."""
    while True:
        await asyncio.sleep(60)
        try:
            ncfg = _notif_cfg()
            cal  = ncfg.get("calendar", {})
            mins = _REMINDER_MINUTES.get(cal.get("reminderTime", "15m"), 15)
            low, high = (mins - 1) * 60, (mins + 1) * 60

            with Session(engine) as session:
                events = session.exec(select(CalendarEvent)).all()
            now = datetime.now()
            for ev in events:
                if not ev.notify or not ev.time:
                    continue
                try:
                    ev_dt = datetime.fromisoformat(f"{ev.date}T{ev.time}:00")
                    delta = (ev_dt - now).total_seconds()
                    if low <= delta <= high:
                        await send_notification(
                            title=f"Reminder: {ev.title}",
                            message=f"{ev.title} starts in {mins} minutes",
                            feature="calendar",
                            event="reminder",
                            tags="calendar",
                        )
                except Exception:
                    pass
        except Exception:
            pass
