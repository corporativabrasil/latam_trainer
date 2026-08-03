from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.api.routes import router
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import User

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == "admin@corporativabrasil.com.br"))
        if not admin:
            db.add(User(name="Administrador", email="admin@corporativabrasil.com.br", password_hash=hash_password("Admin@123")))
            db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {"app": settings.app_name, "status": "online", "docs": "/docs"}
