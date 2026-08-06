import json
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import GlossaryTerm, InstructorManual, Material, PracticeMessage, PracticeSession, Project, StudySession, Translation, User, VirtualParticipant
from app.schemas import (
    GenerateRequest, GlossaryCreate, GlossaryOut, LoginRequest, MaterialOut, ProjectCreate, ProjectOut,
    PracticeSessionOut, SimulationRequest, TokenResponse, TranslationCreate, TranslationOut, TranslationUpdate, UserOut,
)
from app.services.ai import AIUnavailableError, ai_service
from app.services.extractor import extract_text
from app.services.simulation_service import (
    SimulationServiceError,
    simulation_service,
)

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())


@router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), _: User = Depends(current_user)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projeto não encontrado")
    return project


@router.get("/projects/{project_id}/materials", response_model=list[MaterialOut])
def list_materials(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return list(db.scalars(select(Material).where(Material.project_id == project_id).order_by(Material.created_at.desc())).all())


@router.post("/projects/{project_id}/materials", response_model=MaterialOut)
def upload_material(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projeto não encontrado")
    extension = Path(file.filename or "arquivo").suffix.lower()
    if extension not in {".pdf", ".docx", ".pptx", ".txt", ".md"}:
        raise HTTPException(400, "Formato não suportado")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    target = upload_dir / stored_name
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    if target.stat().st_size > settings.max_upload_mb * 1024 * 1024:
        target.unlink(missing_ok=True)
        raise HTTPException(413, "Arquivo excede o limite configurado")
    try:
        text = extract_text(str(target))
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(400, f"Falha ao extrair o arquivo: {exc}") from exc
    material = Material(project_id=project_id, filename=file.filename or stored_name, content_type=file.content_type or "", file_path=str(target), extracted_text=text)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.post("/materials/{material_id}/translations", response_model=TranslationOut)
def translate_material(material_id: int, payload: TranslationCreate, db: Session = Depends(get_db), _: User = Depends(current_user)):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(404, "Material não encontrado")
    project = db.get(Project, material.project_id)
    glossary = list(db.scalars(select(GlossaryTerm).where(GlossaryTerm.project_id == project.id)).all())
    source = (payload.source_text or material.extracted_text).strip()
    if not source:
        raise HTTPException(400, "O material não possui texto extraído")
    try:
        translated = ai_service.translate(text=source, project=project, glossary=glossary, mode=payload.mode)
    except AIUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    item = Translation(material_id=material.id, mode=payload.mode, source_text=source, translated_text=translated)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/materials/{material_id}/translations", response_model=list[TranslationOut])
def list_translations(material_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return list(db.scalars(select(Translation).where(Translation.material_id == material_id).order_by(Translation.created_at.desc())).all())


@router.put("/translations/{translation_id}", response_model=TranslationOut)
def update_translation(translation_id: int, payload: TranslationUpdate, db: Session = Depends(get_db), _: User = Depends(current_user)):
    item = db.get(Translation, translation_id)
    if not item:
        raise HTTPException(404, "Tradução não encontrada")
    item.translated_text = payload.translated_text
    item.approved = payload.approved
    db.commit()
    db.refresh(item)
    return item


@router.get("/projects/{project_id}/glossary", response_model=list[GlossaryOut])
def list_glossary(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return list(db.scalars(select(GlossaryTerm).where(GlossaryTerm.project_id == project_id).order_by(GlossaryTerm.source_term)).all())


@router.post("/projects/{project_id}/glossary", response_model=GlossaryOut)
def create_glossary(project_id: int, payload: GlossaryCreate, db: Session = Depends(get_db), _: User = Depends(current_user)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projeto não encontrado")
    existing = db.scalar(select(GlossaryTerm).where(GlossaryTerm.project_id == project_id, GlossaryTerm.source_term == payload.source_term))
    if existing:
        existing.target_term = payload.target_term
        existing.notes = payload.notes
        db.commit(); db.refresh(existing)
        return existing
    term = GlossaryTerm(project_id=project_id, **payload.model_dump())
    db.add(term); db.commit(); db.refresh(term)
    return term


@router.delete("/glossary/{term_id}")
def delete_glossary(term_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    term = db.get(GlossaryTerm, term_id)
    if not term:
        raise HTTPException(404, "Termo não encontrado")
    db.delete(term); db.commit()
    return {"ok": True}


@router.post("/generate")
def generate(payload: GenerateRequest, db: Session = Depends(get_db), _: User = Depends(current_user)):
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(404, "Projeto não encontrado")
    material = db.get(Material, payload.material_id) if payload.material_id else db.scalar(select(Material).where(Material.project_id == project.id).order_by(Material.created_at.desc()))
    if not material:
        raise HTTPException(400, "Envie um material antes de gerar o roteiro")
    try:
        content = ai_service.generate_instructor_script(project=project, text=material.extracted_text)
    except AIUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    manual = InstructorManual(project_id=project.id, material_id=material.id, title=f"Manual — {material.filename}", content=content)
    db.add(manual); db.commit(); db.refresh(manual)
    return {"kind": payload.kind, "id": manual.id, "content": content}


def _safe_json(value: str) -> dict:
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}


def _message_payload(item: PracticeMessage) -> dict:
    return {
        "id": item.id,
        "role": item.role,
        "content": item.content,
        "message_type": item.message_type,
        "metadata": _safe_json(item.metadata_json),
        "created_at": item.created_at,
    }


def _participant_payload(item: VirtualParticipant) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "role": item.role,
        "personality": item.personality,
        "behavior": item.behavior,
        "expertise_level": item.expertise_level,
        "emotion": item.emotion,
        "avatar_code": item.avatar_code,
        "is_active": item.is_active,
    }


def _practice_session_payload(item: PracticeSession) -> dict:
    return {
        "id": item.id,
        "project_id": item.project_id,
        "participant_profile": item.participant_profile,
        "difficulty": item.difficulty,
        "question": item.question,
        "answer": item.answer,
        "feedback": item.feedback,
        "improved_answer": item.improved_answer,
        "scores": _safe_json(item.scores_json),
        "overall": item.overall,
        "status": item.status,
        "messages": [_message_payload(m) for m in item.messages],
        "participants": [_participant_payload(p) for p in item.participants],
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _training_context(project_id: int, db: Session) -> str:
    translations = db.scalars(
        select(Translation).join(Material).where(Material.project_id == project_id)
        .order_by(Translation.approved.desc(), Translation.created_at.desc())
    ).all()
    manuals = db.scalars(
        select(InstructorManual).where(InstructorManual.project_id == project_id)
        .order_by(InstructorManual.updated_at.desc())
    ).all()
    materials = db.scalars(
        select(Material).where(Material.project_id == project_id)
        .order_by(Material.created_at.desc())
    ).all()

    parts = [x.translated_text for x in translations[:3] if x.translated_text]
    parts += [x.content for x in manuals[:2] if x.content]
    if not parts:
        parts += [x.extracted_text for x in materials[:2] if x.extracted_text]
    return "\n\n".join(parts)[:24000]


def _conversation(session: PracticeSession) -> str:
    return "\n".join(f"{m.role}: {m.content}" for m in session.messages)


def _participant_private_data(session: PracticeSession) -> str:
    return json.dumps(
        [
            {
                "name": p.name,
                "role": p.role,
                "personality": p.personality,
                "behavior": p.behavior,
                "hidden_objective": p.hidden_objective,
                "expertise_level": p.expertise_level,
                "emotion": p.emotion,
            }
            for p in session.participants
        ],
        ensure_ascii=False,
    )


def _normalize_difficulty(value: str) -> str:
    normalized = str(value or "").strip().lower()

    mapping = {
        "beginner": "iniciante",
        "intermediate": "intermediário",
        "advanced": "avançado",
        "iniciante": "iniciante",
        "intermediario": "intermediário",
        "intermediário": "intermediário",
        "avancado": "avançado",
        "avançado": "avançado",
    }

    return mapping.get(normalized, "intermediário")


@router.post("/simulation")
def simulation(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    try:
        return simulation_service.run(
            payload=payload,
            db=db,
        )
    except SimulationServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "message": exc.detail,
                "trace_id": exc.trace_id,
            },
        ) from exc


@router.post("/projects/{project_id}/spanish-lab/generate")
def generate_spanish_lab(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projeto não encontrado")
    context = _training_context(project_id, db)
    if not context:
        raise HTTPException(400, "O treinamento ainda não possui material, tradução ou manual processado.")
    try:
        content = ai_service.generate_spanish_lab(project=project, training_context=context)
    except AIUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    required = ("words", "terms", "phrases", "writing_exercises")
    if not all(isinstance(content.get(key), list) for key in required):
        raise HTTPException(502, "A IA não retornou a estrutura completa do laboratório.")
    return {"project_id": project_id, "project_title": project.title, "country": project.country, **content}

@router.post("/projects/{project_id}/spanish-lab/evaluate-writing")
def evaluate_spanish_lab_writing(project_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projeto não encontrado")
    prompt = str(payload.get("prompt", "")).strip()
    answer = str(payload.get("answer", "")).strip()
    reference_answer = str(payload.get("reference_answer", "")).strip()
    if not prompt or not answer:
        raise HTTPException(400, "Exercício e resposta são obrigatórios")
    try:
        evaluation = ai_service.evaluate_spanish_writing(project=project, prompt=prompt, answer=answer, reference_answer=reference_answer)
    except AIUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    overall = max(0, min(100, int(evaluation.get("overall", 0) or 0)))
    db.add(StudySession(project_id=project_id, session_type="escrita_espanhol", score=overall, notes=json.dumps(evaluation, ensure_ascii=False)[:4000]))
    db.commit()
    return evaluation


@router.get("/projects/{project_id}/practice/latest", response_model=PracticeSessionOut | None)
def latest_practice_session(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    item = db.scalar(
        select(PracticeSession)
        .where(PracticeSession.project_id == project_id)
        .order_by(PracticeSession.updated_at.desc(), PracticeSession.id.desc())
    )
    return _practice_session_payload(item) if item else None


@router.get("/projects/{project_id}/practice/history", response_model=list[PracticeSessionOut])
def practice_history(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    items = db.scalars(
        select(PracticeSession)
        .where(PracticeSession.project_id == project_id)
        .order_by(PracticeSession.updated_at.desc(), PracticeSession.id.desc())
    ).all()
    return [_practice_session_payload(item) for item in items]


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return {
        "projects": db.scalar(select(func.count(Project.id))) or 0,
        "materials": db.scalar(select(func.count(Material.id))) or 0,
        "translations": db.scalar(select(func.count(Translation.id))) or 0,
        "approved": db.scalar(select(func.count(Translation.id)).where(Translation.approved.is_(True))) or 0,
        "study_sessions": db.scalar(select(func.count(StudySession.id))) or 0,
    }



@router.post("/pronunciation/transcribe")
async def pronunciation_transcribe(
    audio: UploadFile = File(...),
    _: User = Depends(current_user),
):
    # Navegadores enviam MIME com parâmetros, por exemplo:
    # audio/webm;codecs=opus. A parte após ";" não deve invalidar o arquivo.
    raw_content_type = (audio.content_type or "").lower().strip()
    base_content_type = raw_content_type.split(";", 1)[0].strip()

    extension_by_type = {
        "audio/webm": ".webm",
        "video/webm": ".webm",
        "audio/ogg": ".ogg",
        "application/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "video/mp4": ".mp4",
        "audio/m4a": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/aac": ".aac",
        "application/octet-stream": ".webm",
    }

    original_suffix = Path(audio.filename or "").suffix.lower()
    suffix = (
        original_suffix
        if original_suffix in {
            ".webm", ".ogg", ".mp4", ".m4a", ".mp3", ".wav", ".aac"
        }
        else extension_by_type.get(base_content_type, ".webm")
    )

    max_bytes = 20 * 1024 * 1024
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temporary:
            temp_path = temporary.name
            total = 0

            while True:
                chunk = await audio.read(1024 * 1024)
                if not chunk:
                    break

                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        413,
                        "O áudio excede o limite de 20 MB.",
                    )

                temporary.write(chunk)

        if not temp_path or Path(temp_path).stat().st_size == 0:
            raise HTTPException(
                400,
                "Nenhum áudio foi recebido.",
            )

        try:
            transcript = ai_service.transcribe_audio(temp_path)
        except AIUnavailableError as exc:
            raise HTTPException(503, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc

        return {
            "transcript": transcript,
            "content_type": raw_content_type,
            "base_content_type": base_content_type,
        }
    finally:
        await audio.close()
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)



@router.post("/pronunciation/evaluate")
def pronunciation_evaluate(payload: dict, db: Session = Depends(get_db), _: User = Depends(current_user)):
    from difflib import SequenceMatcher
    import re
    expected = str(payload.get("expected", "")).strip()
    transcript = str(payload.get("transcript", "")).strip()
    project_id = int(payload.get("project_id", 0) or 0)
    if not expected or not transcript:
        raise HTTPException(400, "Frase esperada e transcrição são obrigatórias")
    normalize = lambda t: re.sub(r"[^a-záéíóúüñ0-9 ]", "", t.lower()).split()
    exp, got = normalize(expected), normalize(transcript)
    accuracy = round(SequenceMatcher(None, exp, got).ratio() * 100)
    missing = [w for w in exp if w not in got]
    extra = [w for w in got if w not in exp]
    result = {"score": accuracy, "expected": expected, "transcript": transcript, "missing": missing, "extra": extra, "feedback": "Pronúncia transcrita com boa correspondência." if accuracy >= 80 else "Repita mais devagar e confira as palavras destacadas."}
    if project_id and db.get(Project, project_id):
        db.add(StudySession(project_id=project_id, session_type="pronuncia", score=accuracy, notes=str(result)[:4000])); db.commit()
    return result

@router.delete("/materials/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(404, "Material não encontrado")
    Path(material.file_path).unlink(missing_ok=True)
    db.delete(material); db.commit()
    return {"ok": True}

@router.get("/projects/{project_id}/progress")
def project_progress(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projeto não encontrado")

    materials = db.scalar(
        select(func.count(Material.id)).where(Material.project_id == project_id)
    ) or 0

    translations = db.scalar(
        select(func.count(Translation.id))
        .join(Material)
        .where(Material.project_id == project_id)
    ) or 0

    approved = db.scalar(
        select(func.count(Translation.id))
        .join(Material)
        .where(
            Material.project_id == project_id,
            Translation.approved.is_(True),
        )
    ) or 0

    manuals = db.scalar(
        select(func.count(InstructorManual.id))
        .where(InstructorManual.project_id == project_id)
    ) or 0

    study_sessions = list(
        db.scalars(
            select(StudySession)
            .where(StudySession.project_id == project_id)
            .order_by(StudySession.created_at.desc())
        ).all()
    )

    practice_sessions = list(
        db.scalars(
            select(PracticeSession)
            .where(PracticeSession.project_id == project_id)
            .order_by(PracticeSession.updated_at.desc())
        ).all()
    )

    pronunciation_records = [
        item for item in study_sessions
        if item.session_type == "pronuncia"
    ]
    simulation_records = [
        item for item in study_sessions
        if item.session_type in {"simulacao_2_0", "simulacao"}
    ]

    pronunciation_scores = [
        int(item.score or 0) for item in pronunciation_records
    ]
    simulation_scores = [
        int(item.score or 0)
        for item in simulation_records
        if int(item.score or 0) > 0
    ]

    pronunciation_average = (
        round(sum(pronunciation_scores) / len(pronunciation_scores))
        if pronunciation_scores else 0
    )
    simulation_average = (
        round(sum(simulation_scores) / len(simulation_scores))
        if simulation_scores else 0
    )

    content_component = 100 if materials > 0 else 0
    translation_component = (
        round((approved / translations) * 100)
        if translations > 0 else 0
    )
    manual_component = 100 if manuals > 0 else 0

    simulation_quantity_score = min(100, len(simulation_records) * 20)
    simulation_component = (
        round(
            simulation_quantity_score * 0.40
            + simulation_average * 0.60
        )
        if simulation_records else 0
    )

    pronunciation_quantity_score = min(
        100, len(pronunciation_records) * 20
    )
    pronunciation_component = (
        round(
            pronunciation_quantity_score * 0.35
            + pronunciation_average * 0.65
        )
        if pronunciation_records else 0
    )

    readiness = round(
        content_component * 0.25
        + translation_component * 0.20
        + manual_component * 0.15
        + simulation_component * 0.25
        + pronunciation_component * 0.15
    )
    readiness = max(0, min(100, readiness))

    if readiness >= 90:
        readiness_label = "Pronto para ministrar"
    elif readiness >= 75:
        readiness_label = "Quase pronto"
    elif readiness >= 60:
        readiness_label = "Em preparação"
    else:
        readiness_label = "Preparação inicial"

    missing_items = []
    if not materials:
        missing_items.append("Enviar e processar o material do treinamento")
    if not translations:
        missing_items.append("Gerar a tradução didática")
    elif approved < translations:
        missing_items.append(
            f"Aprovar {translations - approved} tradução(ões) pendente(s)"
        )
    if not manuals:
        missing_items.append("Criar e revisar o manual do instrutor")
    if len(simulation_records) < 3:
        missing_items.append(
            f"Realizar mais {3 - len(simulation_records)} simulação(ões)"
        )
    if simulation_average < 80:
        missing_items.append(
            "Elevar a média das simulações para pelo menos 80"
        )
    if len(pronunciation_records) < 3:
        missing_items.append(
            f"Realizar mais {3 - len(pronunciation_records)} "
            "prática(s) de pronúncia"
        )
    if pronunciation_average < 85:
        missing_items.append(
            "Elevar a média de pronúncia para pelo menos 85"
        )

    strengths = []
    if content_component == 100:
        strengths.append("Conteúdo do treinamento processado")
    if translation_component == 100:
        strengths.append("Traduções revisadas e aprovadas")
    if manual_component == 100:
        strengths.append("Manual do instrutor disponível")
    if simulation_average >= 85:
        strengths.append("Boa condução nas simulações")
    if pronunciation_average >= 90:
        strengths.append("Excelente correspondência de pronúncia")

    attention_points = []
    if translation_component < 100:
        attention_points.append("Revisão e aprovação das traduções")
    if simulation_records and simulation_average < 80:
        attention_points.append(
            "Clareza, didática e condução da turma"
        )
    if pronunciation_records and pronunciation_average < 85:
        attention_points.append(
            "Pronúncia e fluência em frases longas"
        )
    if not simulation_records:
        attention_points.append("Prática de respostas espontâneas")
    if not pronunciation_records:
        attention_points.append("Prática oral em espanhol")

    recommendations = []
    if translation_component < 100:
        recommendations.append(
            "Revise e aprove as traduções pendentes antes de avançar."
        )
    if manual_component < 100:
        recommendations.append(
            "Crie o manual do instrutor para organizar a fala "
            "e os exemplos."
        )
    if simulation_average < 80 or len(simulation_records) < 3:
        recommendations.append(
            "Realize uma nova simulação com participantes resistentes "
            "ou nível avançado."
        )
    if (
        pronunciation_average < 85
        or len(pronunciation_records) < 3
    ):
        recommendations.append(
            "Pratique frases longas e termos técnicos no laboratório "
            "de pronúncia."
        )
    if readiness >= 90:
        recommendations.append(
            "Faça uma simulação final completa antes de ministrar "
            "o treinamento."
        )
    if not recommendations:
        recommendations.append(
            "Mantenha uma rotina curta de simulação e pronúncia."
        )

    latest_activities = []
    labels = {
        "pronuncia": "Prática de pronúncia",
        "simulacao_2_0": "Simulação com turma virtual",
        "simulacao": "Simulação com IA",
    }

    for item in study_sessions[:8]:
        latest_activities.append({
            "type": item.session_type,
            "label": labels.get(
                item.session_type,
                "Atividade de preparação",
            ),
            "score": int(item.score or 0),
            "created_at": item.created_at,
        })

    if not latest_activities:
        for item in practice_sessions[:5]:
            latest_activities.append({
                "type": "practice_session",
                "label": "Sessão de simulação",
                "score": (
                    int(item.overall)
                    if int(item.overall or 0) > 0
                    else None
                ),
                "created_at": item.updated_at,
            })

    all_scores = [
        int(item.score or 0)
        for item in study_sessions
        if item.score is not None
    ]
    average_score = (
        round(sum(all_scores) / len(all_scores))
        if all_scores else 0
    )

    return {
        "version": "progress-2.0",
        "materials": materials,
        "translations": translations,
        "approved": approved,
        "manuals": manuals,
        "simulations": len(simulation_records),
        "pronunciation_sessions": len(pronunciation_records),
        "practice_sessions": len(practice_sessions),
        "average_score": average_score,
        "pronunciation_average": pronunciation_average,
        "simulation_average": simulation_average,
        "readiness": readiness,
        "readiness_label": readiness_label,
        "components": {
            "content": content_component,
            "translation": translation_component,
            "manual": manual_component,
            "simulation": simulation_component,
            "pronunciation": pronunciation_component,
        },
        "missing_items": missing_items,
        "strengths": strengths,
        "attention_points": attention_points,
        "recommendations": recommendations,
        "latest_activities": latest_activities,
    }


@router.get("/projects/{project_id}/manuals")
def list_manuals(project_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [{"id":m.id,"project_id":m.project_id,"material_id":m.material_id,"title":m.title,"content":m.content,"created_at":m.created_at,"updated_at":m.updated_at} for m in db.scalars(select(InstructorManual).where(InstructorManual.project_id == project_id).order_by(InstructorManual.updated_at.desc())).all()]

@router.put("/manuals/{manual_id}")
def update_manual(manual_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(current_user)):
    manual=db.get(InstructorManual,manual_id)
    if not manual: raise HTTPException(404,"Manual não encontrado")
    manual.content=str(payload.get("content",manual.content)); manual.title=str(payload.get("title",manual.title))
    db.commit(); db.refresh(manual)
    return {"id":manual.id,"title":manual.title,"content":manual.content,"updated_at":manual.updated_at}