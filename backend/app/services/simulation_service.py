from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    InstructorManual,
    Material,
    PracticeMessage,
    PracticeSession,
    Project,
    StudySession,
    Translation,
    VirtualParticipant,
)
from app.services.ai import AIUnavailableError, ai_service
from app.services.score_utils import (
    average_positive_scores,
    safe_score,
    safe_score_dict,
)

logger = logging.getLogger("corporativa.simulation")


@dataclass
class SimulationServiceError(Exception):
    detail: str
    status_code: int = 500
    trace_id: str = ""

    def __str__(self) -> str:
        return self.detail


class SimulationService:
    def run(self, *, payload, db: Session) -> dict:
        trace_id = f"SIM-{uuid4().hex[:10].upper()}"

        try:
            project = self._load_project(
                project_id=payload.project_id,
                db=db,
                trace_id=trace_id,
            )
            context = self._training_context(project.id, db)
            if not context:
                raise SimulationServiceError(
                    "O treinamento ainda não possui conteúdo processado.",
                    400,
                    trace_id,
                )

            difficulty = self._normalize_difficulty(payload.difficulty)
            session_id = getattr(payload, "session_id", None)

            if not session_id:
                return self._start_session(
                    project=project,
                    context=context,
                    difficulty=difficulty,
                    classroom_size=self._classroom_size(payload),
                    db=db,
                    trace_id=trace_id,
                )

            return self._continue_session(
                project=project,
                context=context,
                payload=payload,
                db=db,
                trace_id=trace_id,
            )
        except SimulationServiceError:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            logger.exception(
                "simulation_unhandled trace_id=%s project_id=%s",
                trace_id,
                getattr(payload, "project_id", None),
            )
            raise SimulationServiceError(
                f"Falha inesperada no simulador. Código: {trace_id}",
                500,
                trace_id,
            ) from exc

    def _load_project(
        self,
        *,
        project_id: int,
        db: Session,
        trace_id: str,
    ) -> Project:
        project = db.get(Project, project_id)
        if not project:
            raise SimulationServiceError(
                "Projeto não encontrado.",
                404,
                trace_id,
            )
        return project

    def _start_session(
        self,
        *,
        project: Project,
        context: str,
        difficulty: str,
        classroom_size: int,
        db: Session,
        trace_id: str,
    ) -> dict:
        logger.info(
            "simulation_start trace_id=%s project_id=%s difficulty=%s participants=%s",
            trace_id,
            project.id,
            difficulty,
            classroom_size,
        )

        try:
            classroom = ai_service.create_classroom(
                project=project,
                difficulty=difficulty,
                classroom_size=classroom_size,
            )
        except AIUnavailableError as exc:
            raise SimulationServiceError(str(exc), 503, trace_id) from exc
        except RuntimeError as exc:
            raise SimulationServiceError(str(exc), 502, trace_id) from exc
        except Exception as exc:
            logger.exception(
                "simulation_create_classroom_failed trace_id=%s",
                trace_id,
            )
            raise SimulationServiceError(
                f"Falha ao criar a turma virtual. Código: {trace_id}",
                502,
                trace_id,
            ) from exc

        classroom = self._normalize_classroom(classroom, classroom_size)
        if not classroom:
            raise SimulationServiceError(
                "A IA não retornou participantes válidos.",
                502,
                trace_id,
            )

        try:
            session = PracticeSession(
                project_id=project.id,
                participant_profile=f"Turma com {len(classroom)} participantes",
                difficulty=difficulty,
                question="Simulação de sala iniciada",
                status="active",
            )
            db.add(session)
            db.flush()

            for participant in classroom:
                db.add(
                    VirtualParticipant(
                        session_id=session.id,
                        name=participant["name"],
                        role=participant["role"],
                        personality=participant["personality"],
                        behavior=participant["behavior"],
                        hidden_objective=participant["hidden_objective"],
                        expertise_level=participant["expertise_level"],
                        emotion=participant["emotion"],
                        avatar_code=participant["avatar_code"],
                    )
                )

            db.flush()
            db.refresh(session)
        except Exception as exc:
            logger.exception(
                "simulation_persist_classroom_failed trace_id=%s",
                trace_id,
            )
            raise SimulationServiceError(
                f"Falha ao salvar a turma virtual. Código: {trace_id}",
                500,
                trace_id,
            ) from exc

        try:
            opening = ai_service.classroom_turn(
                project=project,
                difficulty=difficulty,
                training_context=context,
                participants_json=self._participant_private_data(session),
                conversation="A sessão acabou de começar.",
                instructor_answer="O instrutor iniciou a apresentação.",
                finish=False,
            )
        except AIUnavailableError as exc:
            raise SimulationServiceError(str(exc), 503, trace_id) from exc
        except RuntimeError as exc:
            raise SimulationServiceError(str(exc), 502, trace_id) from exc
        except Exception as exc:
            logger.exception(
                "simulation_opening_failed trace_id=%s",
                trace_id,
            )
            raise SimulationServiceError(
                f"Falha ao gerar a pergunta inicial. Código: {trace_id}",
                502,
                trace_id,
            ) from exc

        replies = self._normalize_replies(opening, session)
        if not replies:
            raise SimulationServiceError(
                "A IA criou a turma, mas não retornou uma pergunta inicial.",
                502,
                trace_id,
            )

        try:
            self._persist_replies(
                session=session,
                replies=replies,
                finish=False,
                db=db,
            )
            db.commit()
            db.refresh(session)
        except Exception as exc:
            logger.exception(
                "simulation_persist_opening_failed trace_id=%s",
                trace_id,
            )
            raise SimulationServiceError(
                f"Falha ao salvar a abertura da turma. Código: {trace_id}",
                500,
                trace_id,
            ) from exc

        logger.info(
            "simulation_started trace_id=%s session_id=%s",
            trace_id,
            session.id,
        )
        return {
            "type": "classroom_started",
            "trace_id": trace_id,
            "session": self._session_payload(session),
        }

    def _continue_session(
        self,
        *,
        project: Project,
        context: str,
        payload,
        db: Session,
        trace_id: str,
    ) -> dict:
        session = db.get(PracticeSession, payload.session_id)
        if not session or session.project_id != project.id:
            raise SimulationServiceError(
                "Sessão não encontrada.",
                404,
                trace_id,
            )
        if session.status == "finished":
            raise SimulationServiceError(
                "A simulação já foi encerrada.",
                400,
                trace_id,
            )

        answer = str(getattr(payload, "user_answer", "") or "").strip()
        if not answer:
            raise SimulationServiceError(
                "Escreva uma resposta antes de continuar.",
                400,
                trace_id,
            )

        finish = str(getattr(payload, "action", "continue")) == "finish"

        try:
            db.add(
                PracticeMessage(
                    session_id=session.id,
                    role="instructor",
                    content=answer,
                    message_type="answer",
                )
            )
            db.flush()
        except Exception as exc:
            logger.exception(
                "simulation_persist_answer_failed trace_id=%s session_id=%s",
                trace_id,
                session.id,
            )
            raise SimulationServiceError(
                f"Falha ao salvar a resposta. Código: {trace_id}",
                500,
                trace_id,
            ) from exc

        try:
            turn = ai_service.classroom_turn(
                project=project,
                difficulty=session.difficulty,
                training_context=context,
                participants_json=self._participant_private_data(session),
                conversation=self._conversation(session),
                instructor_answer=answer,
                finish=finish,
            )
        except AIUnavailableError as exc:
            raise SimulationServiceError(str(exc), 503, trace_id) from exc
        except RuntimeError as exc:
            raise SimulationServiceError(str(exc), 502, trace_id) from exc
        except Exception as exc:
            logger.exception(
                "simulation_turn_failed trace_id=%s session_id=%s",
                trace_id,
                session.id,
            )
            raise SimulationServiceError(
                f"Falha ao gerar a reação da turma. Código: {trace_id}",
                502,
                trace_id,
            ) from exc

        hidden = turn.get("hidden_evaluation")
        if not isinstance(hidden, dict):
            hidden = {}

        hidden = self._normalize_hidden_evaluation(hidden)

        try:
            db.add(
                PracticeMessage(
                    session_id=session.id,
                    role="evaluation",
                    content=str(hidden.get("feedback", "")),
                    message_type="hidden_evaluation",
                    metadata_json=json.dumps(hidden, ensure_ascii=False),
                )
            )

            replies = self._normalize_replies(turn, session)
            self._persist_replies(
                session=session,
                replies=replies,
                finish=finish,
                db=db,
            )
        except Exception as exc:
            logger.exception(
                "simulation_persist_turn_failed trace_id=%s session_id=%s",
                trace_id,
                session.id,
            )
            raise SimulationServiceError(
                f"Falha ao salvar a interação. Código: {trace_id}",
                500,
                trace_id,
            ) from exc

        should_finish = finish or not bool(
            turn.get("continue_conversation", True)
        )

        if should_finish:
            self._finish_session(
                project=project,
                session=session,
                db=db,
                trace_id=trace_id,
            )

        try:
            db.commit()
            db.refresh(session)
        except Exception as exc:
            logger.exception(
                "simulation_commit_failed trace_id=%s session_id=%s",
                trace_id,
                session.id,
            )
            raise SimulationServiceError(
                f"Falha ao concluir a gravação. Código: {trace_id}",
                500,
                trace_id,
            ) from exc

        logger.info(
            "simulation_turn_completed trace_id=%s session_id=%s status=%s",
            trace_id,
            session.id,
            session.status,
        )
        return {
            "type": "classroom_turn",
            "trace_id": trace_id,
            "session": self._session_payload(session),
        }

    def _finish_session(
        self,
        *,
        project: Project,
        session: PracticeSession,
        db: Session,
        trace_id: str,
    ) -> None:
        db.flush()

        evaluations = [
            self._safe_json(message.metadata_json)
            for message in session.messages
            if message.message_type == "hidden_evaluation"
        ]

        try:
            report = ai_service.final_report(
                project=project,
                participants_json=self._participant_private_data(session),
                conversation=self._conversation(session),
                evaluations_json=json.dumps(
                    evaluations,
                    ensure_ascii=False,
                ),
            )
        except AIUnavailableError as exc:
            raise SimulationServiceError(str(exc), 503, trace_id) from exc
        except RuntimeError as exc:
            raise SimulationServiceError(str(exc), 502, trace_id) from exc
        except Exception as exc:
            logger.exception(
                "simulation_final_report_failed trace_id=%s session_id=%s",
                trace_id,
                session.id,
            )
            raise SimulationServiceError(
                f"Falha ao gerar o relatório final. Código: {trace_id}",
                502,
                trace_id,
            ) from exc

        if not isinstance(report, dict):
            report = {}

        clean_scores = safe_score_dict(report.get("scores", {}))
        overall = safe_score(report.get("overall"))
        if overall == 0:
            overall = average_positive_scores(clean_scores)

        coach_summary = report.get("coach_summary")
        if not isinstance(coach_summary, str) or not coach_summary.strip():
            raw_overall = report.get("overall")
            coach_summary = (
                str(raw_overall).strip()
                if isinstance(raw_overall, str)
                else (
                    "Simulação concluída. Consulte os indicadores "
                    "e recomendações."
                )
            )

        normalized_report = dict(report)
        normalized_report["overall"] = overall
        normalized_report["scores"] = clean_scores
        normalized_report["coach_summary"] = coach_summary

        session.status = "finished"
        session.overall = overall
        session.scores_json = json.dumps(
            clean_scores,
            ensure_ascii=False,
        )
        session.feedback = coach_summary

        db.add(
            PracticeMessage(
                session_id=session.id,
                role="coach",
                content=coach_summary,
                message_type="final_report",
                metadata_json=json.dumps(
                    normalized_report,
                    ensure_ascii=False,
                ),
            )
        )
        db.add(
            StudySession(
                project_id=project.id,
                session_type="simulacao_2_0",
                score=overall,
                notes=json.dumps(
                    normalized_report,
                    ensure_ascii=False,
                )[:4000],
            )
        )

    def _training_context(self, project_id: int, db: Session) -> str:
        translations = db.scalars(
            select(Translation)
            .join(Material)
            .where(Material.project_id == project_id)
            .order_by(
                Translation.approved.desc(),
                Translation.created_at.desc(),
            )
        ).all()

        manuals = db.scalars(
            select(InstructorManual)
            .where(InstructorManual.project_id == project_id)
            .order_by(InstructorManual.updated_at.desc())
        ).all()

        materials = db.scalars(
            select(Material)
            .where(Material.project_id == project_id)
            .order_by(Material.created_at.desc())
        ).all()

        parts = [
            item.translated_text
            for item in translations[:3]
            if item.translated_text
        ]
        parts += [
            item.content
            for item in manuals[:2]
            if item.content
        ]
        if not parts:
            parts += [
                item.extracted_text
                for item in materials[:2]
                if item.extracted_text
            ]

        return "\n\n".join(parts)[:24000]

    @staticmethod
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

    @staticmethod
    def _classroom_size(payload) -> int:
        raw = getattr(payload, "classroom_size", 1)
        try:
            return max(1, min(6, int(raw)))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _normalize_classroom(
        classroom,
        classroom_size: int,
    ) -> list[dict]:
        if not isinstance(classroom, list):
            return []

        normalized = []
        for index, item in enumerate(classroom[:classroom_size]):
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).strip()
            if not name:
                name = f"Participante {index + 1}"

            initials = "".join(
                part[0]
                for part in name.split()
                if part
            )[:2].upper() or "VP"

            normalized.append({
                "name": name[:60],
                "role": str(
                    item.get("role", "Colaborador")
                ).strip()[:60],
                "personality": str(
                    item.get("personality", "pragmático")
                ).strip()[:60],
                "behavior": str(
                    item.get("behavior", "")
                ).strip()[:60],
                "hidden_objective": str(
                    item.get("hidden_objective", "")
                ).strip()[:60],
                "expertise_level": str(
                    item.get("expertise_level", "intermediário")
                ).strip()[:60],
                "emotion": str(
                    item.get("emotion", "neutro")
                ).strip()[:60],
                "avatar_code": str(
                    item.get("avatar_code", initials)
                ).strip()[:8],
            })

        return normalized

    def _normalize_replies(
        self,
        value,
        session: PracticeSession,
    ) -> list[dict]:
        if not isinstance(value, dict):
            return []

        replies = value.get("replies")
        if not isinstance(replies, list):
            replies = []

        if not replies:
            legacy_reply = str(
                value.get("participant_reply", "")
            ).strip()
            if legacy_reply:
                default_name = (
                    session.participants[0].name
                    if session.participants
                    else "Participante"
                )
                replies = [{
                    "speaker_name": str(
                        value.get("speaker_name", default_name)
                    ),
                    "participant_reply": legacy_reply,
                    "reaction_type": str(
                        value.get("reaction_type", "follow_up")
                    ),
                    "emotion": "neutral",
                }]

        normalized = []
        for item in replies[:3]:
            if not isinstance(item, dict):
                continue

            reply = str(
                item.get("participant_reply", "")
            ).strip()
            if not reply:
                continue

            normalized.append({
                "speaker_name": str(
                    item.get("speaker_name", "Participante")
                ),
                "participant_reply": reply,
                "reaction_type": str(
                    item.get("reaction_type", "follow_up")
                ),
                "emotion": str(
                    item.get("emotion", "neutral")
                ),
            })

        return normalized

    @staticmethod
    def _normalize_hidden_evaluation(value: dict) -> dict:
        result = dict(value)
        raw_scores = result.get("scores", {})

        if isinstance(raw_scores, dict):
            result["scores"] = safe_score_dict(raw_scores)
        else:
            direct_scores = {
                key: safe_score(result.get(key))
                for key in (
                    "comprehension",
                    "spanish",
                    "content",
                    "clarity",
                    "didactics",
                    "empathy",
                    "classroom_control",
                    "examples",
                    "engagement",
                )
                if result.get(key) is not None
            }
            result["scores"] = direct_scores

        result["feedback"] = str(result.get("feedback", ""))
        result["improved_answer"] = str(
            result.get("improved_answer", "")
        )
        return result

    @staticmethod
    def _persist_replies(
        *,
        session: PracticeSession,
        replies: list[dict],
        finish: bool,
        db: Session,
    ) -> None:
        for item in replies:
            db.add(
                PracticeMessage(
                    session_id=session.id,
                    role="participant",
                    content=item["participant_reply"],
                    message_type=(
                        "closing"
                        if finish
                        else item["reaction_type"]
                    ),
                    metadata_json=json.dumps(
                        {
                            "speaker_name": item["speaker_name"],
                            "emotion": item["emotion"],
                        },
                        ensure_ascii=False,
                    ),
                )
            )

    @staticmethod
    def _safe_json(value: str) -> dict:
        try:
            parsed = json.loads(value or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _conversation(self, session: PracticeSession) -> str:
        return "\n".join(
            f"{message.role}: {message.content}"
            for message in session.messages
        )

    @staticmethod
    def _participant_private_data(
        session: PracticeSession,
    ) -> str:
        return json.dumps(
            [
                {
                    "name": participant.name,
                    "role": participant.role,
                    "personality": participant.personality,
                    "behavior": participant.behavior,
                    "hidden_objective": participant.hidden_objective,
                    "expertise_level": participant.expertise_level,
                    "emotion": participant.emotion,
                }
                for participant in session.participants
            ],
            ensure_ascii=False,
        )

    def _session_payload(self, item: PracticeSession) -> dict:
        return {
            "id": item.id,
            "project_id": item.project_id,
            "participant_profile": item.participant_profile,
            "difficulty": item.difficulty,
            "question": item.question,
            "answer": item.answer,
            "feedback": item.feedback,
            "improved_answer": item.improved_answer,
            "scores": self._safe_json(item.scores_json),
            "overall": item.overall,
            "status": item.status,
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "message_type": message.message_type,
                    "metadata": self._safe_json(
                        message.metadata_json
                    ),
                    "created_at": message.created_at,
                }
                for message in item.messages
            ],
            "participants": [
                {
                    "id": participant.id,
                    "name": participant.name,
                    "role": participant.role,
                    "personality": participant.personality,
                    "behavior": participant.behavior,
                    "expertise_level": participant.expertise_level,
                    "emotion": participant.emotion,
                    "avatar_code": participant.avatar_code,
                    "is_active": participant.is_active,
                }
                for participant in item.participants
            ],
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }


simulation_service = SimulationService()