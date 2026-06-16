from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    connect_args={"check_same_thread": False},  # required for SQLite + async FastAPI
)


def init_db() -> None:
    from app.routers.logs import LogEntry                              # noqa
    from app.routers.automations import Automation, AutomationLog     # noqa
    SQLModel.metadata.create_all(engine)
    from app.routers.notifications import ensure_table
    ensure_table()


def get_session():
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
