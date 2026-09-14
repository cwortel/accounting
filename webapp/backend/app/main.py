from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from . import models  # noqa: F401  (ensures models are registered on Base before create_all)
from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import accounts, bank, categories, expenses, income, private, reports
from .routers import settings as settings_router


def _run_lightweight_migrations() -> None:
    """Add columns to existing tables that create_all() won't touch."""
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE bank_transactions ADD COLUMN bank_ref TEXT NOT NULL DEFAULT ''"))
        except OperationalError:
            pass  # column already exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()
    with SessionLocal() as db:
        for naam in categories.DEFAULT_CATEGORIES:
            if not db.query(models.Category).filter_by(naam=naam).first():
                db.add(models.Category(naam=naam))
        db.commit()
    yield


app = FastAPI(title="Green Light Boekhouding API", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(expenses.router)
app.include_router(income.router)
app.include_router(categories.router)
app.include_router(accounts.router)
app.include_router(bank.router)
app.include_router(reports.router)
app.include_router(private.router)
app.include_router(settings_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
