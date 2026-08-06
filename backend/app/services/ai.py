import json
from openai import OpenAI
from app.core.config import settings


class AIUnavailableError(RuntimeError):
    pass


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    @staticmethod
    def _parse_json(raw: str, expected_type: type):
        text = (raw or "").strip()
        if not text:
            raise RuntimeError("A IA retornou uma resposta vazia.")

        # Remove blocos Markdown comuns: ```json ... ``` ou ``` ... ```
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Primeira tentativa: conteúdo inteiro já é JSON.
        try:
            data = json.loads(text)
            if isinstance(data, expected_type):
                return data
        except json.JSONDecodeError:
            pass

        # Segunda tentativa: encontra o primeiro objeto/lista JSON dentro do texto.
        decoder = json.JSONDecoder()
        opening = "[" if expected_type is list else "{"
        for index, char in enumerate(text):
            if char != opening:
                continue
            try:
                data, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(data, expected_type):
                return data

        preview = text[:500].replace("\n", " ")
        raise RuntimeError(
            f"A IA não retornou JSON válido. Início da resposta: {preview}"
        )

    def _call_json(
        self,
        *,
        system: str,
        user: str,
        expected_type: type,
    ):
        raw = self._call(system, user)
        try:
            return self._parse_json(raw, expected_type)
        except RuntimeError:
            # Uma segunda tentativa reduz falhas quando o modelo acrescenta
            # explicações, Markdown ou texto antes do JSON.
            retry_system = (
                system
                + " Responda obrigatoriamente somente com JSON válido, sem "
                  "blocos Markdown, sem comentários e sem texto antes ou depois."
            )
            retry_user = (
                user
                + "\n\nA resposta anterior não pôde ser interpretada. "
                  "Gere novamente apenas o JSON solicitado."
            )
            retry_raw = self._call(retry_system, retry_user)
            return self._parse_json(retry_raw, expected_type)

    def _call(self, system: str, user: str) -> str:
        if not self.client:
            raise AIUnavailableError("Configure OPENAI_API_KEY no arquivo .env para usar os recursos de IA.")
        response = self.client.responses.create(
            model=settings.openai_model,
            instructions=system,
            input=user,
        )
        text = (response.output_text or "").strip()
        if not text:
            raise RuntimeError("A IA não retornou conteúdo.")
        return text

    @staticmethod
    def _looks_portuguese(text: str) -> bool:
        sample = f" {str(text or '').lower()} "
        portuguese_markers = (
            " poderia ", " pouco ", " mais ", " como o ", " evolução ",
            " gestão ", " chão de fábrica ", " sua resposta ", " não ",
            " dúvida ", " exemplo prático ", " poderia detalhar ", " hoje ",
            " liderança ", " plantas industriais ", " para que ",
        )
        spanish_markers = (
            " podría ", " un poco ", " cómo ", " evolución ", " gestión ",
            " planta ", " su respuesta ", " no ", " duda ",
            " ejemplo práctico ", " podría detallar ", " hoy ", " liderazgo ",
        )
        pt_score = sum(marker in sample for marker in portuguese_markers)
        es_score = sum(marker in sample for marker in spanish_markers)
        return pt_score >= 2 and pt_score > es_score

    def _ensure_spanish(self, text: str, *, country: str = "Latinoamérica") -> str:
        cleaned = str(text or "").strip()
        if not cleaned or not self._looks_portuguese(cleaned):
            return cleaned

        try:
            translated = self._call(
                (
                    "Traduza exclusivamente para espanhol latino-americano natural. "
                    "Não explique, não acrescente conteúdo e não use português. "
                    "Retorne somente o texto traduzido."
                ),
                f"País de destino: {country}\n\nTexto a traduzir:\n{cleaned}",
            ).strip()

            return translated or cleaned
        except Exception:
            # Uma falha na tradução corretiva não deve interromper
            # toda a simulação. Mantém o texto original.
            return cleaned

    def transcribe_audio(self, file_path: str) -> str:
        """Transcreve áudio em espanhol usando a API de transcrição da OpenAI."""
        if not self.client:
            raise AIUnavailableError(
                "Configure OPENAI_API_KEY para transcrever o áudio."
            )

        model = getattr(
            settings,
            "openai_transcription_model",
            "gpt-4o-mini-transcribe",
        )

        try:
            with open(file_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language="es",
                    response_format="json",
                )
        except Exception as exc:
            raise RuntimeError(
                f"Não foi possível transcrever o áudio: {exc}"
            ) from exc

        if isinstance(response, dict):
            text = str(response.get("text", "")).strip()
        else:
            text = str(getattr(response, "text", "")).strip()

        if not text:
            raise RuntimeError(
                "A transcrição foi concluída, mas nenhum texto foi reconhecido."
            )

        return text


    def translate(self, *, text: str, project, glossary: list, mode: str) -> str:
        glossary_text = "\n".join(
            f"- {g.source_term} = {g.target_term} ({g.notes})" for g in glossary
        ) or "Sem glossário cadastrado."
        return self._call(
            "Você é tradutor de treinamentos industriais. Traduza para espanhol latino-americano natural e preserve a estrutura.",
            f"Projeto: {project.title}\nPaís: {project.country}\nGlossário:\n{glossary_text}\n\nTexto:\n{text}",
        )

    def generate_instructor_script(self, *, project, text: str) -> str:
        return self._call(
            "Crie um manual prático em espanhol para um instrutor brasileiro. Use somente o conteúdo fornecido.",
            f"Treinamento: {project.title}\nPaís: {project.country}\nPúblico: {project.audience}\n\n{text}",
        )

    def generate_spanish_lab(self, *, project, training_context: str) -> dict:
        system = (
            "Você é especialista em espanhol corporativo para instrutores brasileiros "
            "que ministram treinamentos industriais na América Latina. Use SOMENTE o "
            "conteúdo fornecido. Retorne SOMENTE JSON válido com words, terms, phrases "
            "e writing_exercises. words deve conter 18 objetos com spanish, portuguese, "
            "context, syllables e example. terms deve conter 12 objetos com source, "
            "target e explanation. phrases deve conter 15 objetos com spanish, "
            "portuguese, use_case e difficulty. writing_exercises deve conter 10 objetos "
            "com type, prompt, reference_answer e difficulty. Tipos: copy, fill_blank, "
            "translate e free_answer. Todo espanhol deve ser natural e adaptado ao país."
        )
        return self._call_json(
            system=system,
            user=(
                f"Treinamento: {project.title}\nPaís: {project.country}\n"
                f"Público: {project.audience}\nObjetivo: {project.objective}\n\n"
                f"CONTEÚDO REAL:\n{training_context[:22000]}"
            ),
            expected_type=dict,
        )

    def evaluate_spanish_writing(self, *, project, prompt: str, answer: str, reference_answer: str) -> dict:
        system = (
            "Avalie uma resposta escrita em espanhol de um instrutor brasileiro. "
            "Retorne SOMENTE JSON válido com overall, grammar, vocabulary, clarity, "
            "naturalness, use_of_training_terms, feedback_pt, corrected_answer e "
            "key_corrections. Notas de 0 a 100. feedback_pt e key_corrections em "
            "português; corrected_answer em espanhol natural e corporativo."
        )
        return self._call_json(
            system=system,
            user=(
                f"Treinamento: {project.title}\nPaís: {project.country}\n"
                f"Exercício: {prompt}\nResposta de referência: {reference_answer}\n"
                f"Resposta do instrutor: {answer}"
            ),
            expected_type=dict,
        )


    def create_classroom(self, *, project, difficulty: str, classroom_size: int) -> list[dict]:
        system = (
            "Crie participantes realistas para uma sala de treinamento industrial latino-americana. "
            "Retorne SOMENTE JSON válido: uma lista com objetos contendo name, role, personality, behavior, "
            "hidden_objective, expertise_level, emotion e avatar_code (duas letras). "
            "Os objetivos ocultos nunca podem aparecer na fala do participante. "
            "Misture perfis curiosos, resistentes, técnicos, tímidos e pragmáticos. "
            "Os campos role, personality, behavior, hidden_objective, expertise_level e emotion "
            "devem ser escritos em espanhol. Os nomes devem ser naturais no país informado."
        )
        data = self._call_json(
            system=system,
            user=(
                f"Treinamento: {project.title}\nEmpresa: {project.client_company}\n"
                f"País: {project.country}\nPúblico: {project.audience}\n"
                f"Dificuldade: {difficulty}\nQuantidade: {classroom_size}"
            ),
            expected_type=list,
        )
        if not isinstance(data, list):
            raise RuntimeError("A IA não retornou uma turma válida.")
        return data[:classroom_size]

    def classroom_turn(
        self,
        *,
        project,
        difficulty: str,
        training_context: str,
        participants_json: str,
        conversation: str,
        instructor_answer: str,
        finish: bool,
    ) -> dict:
        system = (
            "Você simula uma turma industrial latino-americana com participantes independentes. "
            "Retorne SOMENTE JSON válido com os campos: replies, hidden_evaluation e continue_conversation. "
            "replies deve ser uma lista de 1 a 3 objetos, cada um com speaker_name, participant_reply, "
            "reaction_type e emotion. "
            "Cada participante deve respeitar sua personalidade, comportamento, nível técnico e objetivo oculto. "
            "Não use sempre o mesmo participante. Alterne os falantes ao longo da conversa. "
            "Se o instrutor mencionar diretamente um participante pelo nome, esse participante deve responder. "
            "Se o instrutor perguntar ao grupo, podem responder 2 ou 3 participantes com perspectivas diferentes. "
            "Os participantes podem concordar, discordar entre si, pedir exemplos, dizer que não entenderam, "
            "apresentar casos reais ou desafiar respostas superficiais. "
            "As falas precisam parecer humanas, curtas e naturais, e não respostas genéricas de assistente. "
            "REGRA OBRIGATÓRIA: participant_reply deve ser exclusivamente em espanhol latino-americano, "
            "adaptado ao país do projeto. Nunca use português nas falas. "
            "hidden_evaluation deve conter scores para comprehension, spanish, content, clarity, didactics, "
            "empathy, classroom_control, examples e engagement, além de feedback em português e improved_answer "
            "em espanhol. A avaliação fica invisível durante a conversa. "
            "Se finish=true, gere uma única despedida e continue_conversation=false."
        )

        result = self._call_json(
            system=system,
            user=f"""TREINAMENTO
{project.title} | {project.country} | {project.audience}
Dificuldade: {difficulty}

CONTEÚDO REAL
{training_context[:14000]}

PARTICIPANTES E PERFIS
{participants_json}

CONVERSA COMPLETA
{conversation[-14000:]}

RESPOSTA ATUAL DO INSTRUTOR
{instructor_answer}

ENCERRAR: {str(finish).lower()}
""",
            expected_type=dict,
        )

        replies = result.get("replies")
        if not isinstance(replies, list):
            legacy_reply = str(result.get("participant_reply", "")).strip()
            replies = [{
                "speaker_name": str(result.get("speaker_name", "Participante")),
                "participant_reply": legacy_reply,
                "reaction_type": str(result.get("reaction_type", "follow_up")),
                "emotion": "neutral",
            }] if legacy_reply else []

        clean_replies = []
        for item in replies[:3]:
            if not isinstance(item, dict):
                continue
            reply = self._ensure_spanish(
                str(item.get("participant_reply", "")),
                country=str(project.country or "Latinoamérica"),
            )
            if not reply:
                continue
            clean_replies.append({
                "speaker_name": str(item.get("speaker_name", "Participante")),
                "participant_reply": reply,
                "reaction_type": str(item.get("reaction_type", "follow_up")),
                "emotion": str(item.get("emotion", "neutral")),
            })

        if not clean_replies:
            raise RuntimeError("A IA não retornou uma reação válida da turma.")

        hidden = result.get("hidden_evaluation")
        if not isinstance(hidden, dict):
            hidden = {}
            result["hidden_evaluation"] = hidden

        hidden["improved_answer"] = self._ensure_spanish(
            str(hidden.get("improved_answer", "")),
            country=str(project.country or "Latinoamérica"),
        )

        result["replies"] = clean_replies
        result["continue_conversation"] = bool(
            result.get("continue_conversation", not finish)
        )
        return result

    def final_report(
        self,
        *,
        project,
        participants_json: str,
        conversation: str,
        evaluations_json: str,
    ) -> dict:
        system = (
            "Gere um relatório profissional final para um instrutor corporativo brasileiro que treinou em espanhol. "
            "Retorne SOMENTE JSON válido com overall, scores, strengths, improvements, critical_moments, "
            "best_moments, unanswered_questions, study_plan e coach_summary. "
            "scores deve conter spanish, content, clarity, didactics, empathy, classroom_control, examples e engagement."
        )
        return self._call_json(
            system=system,
            user=(
                f"Treinamento: {project.title}\nPaís: {project.country}\n"
                f"Participantes: {participants_json}\n"
                f"Conversa:\n{conversation[-16000:]}\n"
                f"Avaliações ocultas:\n{evaluations_json[-12000:]}"
            ),
            expected_type=dict,
        )


ai_service = AIService()
