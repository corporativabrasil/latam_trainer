from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    client_company: Mapped[str] = mapped_column(String(180), default="")
    country: Mapped[str] = mapped_column(String(80), default="Latinoamérica")
    audience: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    spanish_variant: Mapped[str] = mapped_column(String(80), default="es-LATAM")
    formality: Mapped[str] = mapped_column(String(40), default="corporativo")
    modality: Mapped[str] = mapped_column(String(40), default="presencial")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    materials: Mapped[list["Material"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    glossary: Mapped[list["GlossaryTerm"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    manuals: Mapped[list["InstructorManual"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    practice_sessions: Mapped[list["PracticeSession"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    file_path: Mapped[str] = mapped_column(String(500))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project: Mapped[Project] = relationship(back_populates="materials")
    translations: Mapped[list["Translation"]] = relationship(back_populates="material", cascade="all, delete-orphan")


class Translation(Base):
    __tablename__ = "translations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(40), default="didatico")
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    material: Mapped[Material] = relationship(back_populates="translations")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"
    __table_args__ = (UniqueConstraint("project_id", "source_term", name="uq_project_source_term"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_term: Mapped[str] = mapped_column(String(180))
    target_term: Mapped[str] = mapped_column(String(180))
    notes: Mapped[str] = mapped_column(Text, default="")
    project: Mapped[Project] = relationship(back_populates="glossary")


class StudySession(Base):
    __tablename__ = "study_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_type: Mapped[str] = mapped_column(String(60))
    score: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InstructorManual(Base):
    __tablename__ = "instructor_manuals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(220), default="Manual do instrutor")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project: Mapped[Project] = relationship(back_populates="manuals")


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    participant_profile: Mapped[str] = mapped_column(String(160), default="Supervisor de produção")
    difficulty: Mapped[str] = mapped_column(String(40), default="intermediário")
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    feedback: Mapped[str] = mapped_column(Text, default="")
    improved_answer: Mapped[str] = mapped_column(Text, default="")
    scores_json: Mapped[str] = mapped_column(Text, default="{}")
    overall: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="question")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project: Mapped[Project] = relationship(back_populates="practice_sessions")
    messages: Mapped[list["PracticeMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PracticeMessage.created_at",
    )
    participants: Mapped[list["VirtualParticipant"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="VirtualParticipant.id",
    )


class PracticeMessage(Base):
    __tablename__ = "practice_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(40), default="message")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    session: Mapped[PracticeSession] = relationship(back_populates="messages")


class VirtualParticipant(Base):
    __tablename__ = "virtual_participants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(140))
    personality: Mapped[str] = mapped_column(String(120))
    behavior: Mapped[str] = mapped_column(Text, default="")
    hidden_objective: Mapped[str] = mapped_column(Text, default="")
    expertise_level: Mapped[str] = mapped_column(String(60), default="intermediário")
    emotion: Mapped[str] = mapped_column(String(40), default="neutro")
    avatar_code: Mapped[str] = mapped_column(String(8), default="VP")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    session: Mapped[PracticeSession] = relationship(back_populates="participants")
