from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    client_company: str = ""
    country: str = "Latinoamérica"
    audience: str = ""
    objective: str = ""
    spanish_variant: str = "es-LATAM"
    formality: str = "corporativo"
    modality: str = "presencial"


class ProjectOut(ProjectCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MaterialOut(BaseModel):
    id: int
    project_id: int
    filename: str
    content_type: str
    status: str
    extracted_text: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TranslationCreate(BaseModel):
    mode: str = "didatico"
    source_text: str | None = None


class TranslationUpdate(BaseModel):
    translated_text: str
    approved: bool = False


class TranslationOut(BaseModel):
    id: int
    material_id: int
    mode: str
    source_text: str
    translated_text: str
    approved: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GlossaryCreate(BaseModel):
    source_term: str
    target_term: str
    notes: str = ""


class GlossaryOut(GlossaryCreate):
    id: int
    project_id: int
    model_config = ConfigDict(from_attributes=True)


class GenerateRequest(BaseModel):
    project_id: int
    material_id: int | None = None
    kind: str = "roteiro"


class SimulationRequest(BaseModel):
    project_id: int
    participant_profile: str = "turma industrial"
    difficulty: str = "intermediário"
    user_answer: str = ""
    session_id: int | None = None
    action: str = "continue"
    classroom_size: int = Field(default=4, ge=1, le=8)


class PracticeMessageOut(BaseModel):
    id: int
    role: str
    content: str
    message_type: str
    metadata: dict
    created_at: datetime


class VirtualParticipantOut(BaseModel):
    id: int
    name: str
    role: str
    personality: str
    behavior: str
    expertise_level: str
    emotion: str
    avatar_code: str
    is_active: bool


class PracticeSessionOut(BaseModel):
    id: int
    project_id: int
    participant_profile: str
    difficulty: str
    question: str
    answer: str
    feedback: str
    improved_answer: str
    scores: dict[str, int]
    overall: int
    status: str
    messages: list[PracticeMessageOut] = []
    participants: list[VirtualParticipantOut] = []
    created_at: datetime
    updated_at: datetime
