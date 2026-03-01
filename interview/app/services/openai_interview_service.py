"""OpenAI-powered interview agent: generates questions by job role and conversation."""

from openai import AsyncOpenAI

from app.config import get_settings


class OpenAIInterviewService:
    """Generate interview questions and follow-ups using OpenAI."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self._model = settings.openai_model

    def is_available(self) -> bool:
        return self._client is not None

    async def get_next_question(
        self,
        job_role: str,
        previous_exchanges: list[dict],
        tech_stack: list[str] | None = None,
    ) -> str:
        """
        Get the next interview question from the AI.
        Covers: role they applied for, tech stack, and communication skills.
        """
        if not self._client:
            return (
                "OpenAI is not configured. Set OPENAI_API_KEY in your .env file to enable the AI interviewer."
            )

        system = (
            "You are a professional interviewer for Company X. Ask one clear question at a time. "
            "Cover: (1) the job role they applied for, (2) their tech stack/skills, and (3) communication skills. "
            "Do not repeat questions. Adapt based on their answers. "
            "Reply with only the next question, no preamble or numbering."
        )

        tech_part = ""
        if tech_stack:
            tech_part = f" Their tech stack/skills: {', '.join(tech_stack)}. Include at least one technical question relevant to their stack and one on communication or teamwork."

        if not previous_exchanges:
            user_content = (
                f"Job role for this interview: {job_role}.{tech_part} "
                "Ask the first interview question (one question only)."
            )
        else:
            history = "\n\n".join(
                f"Q: {ex['question']}\nA: {ex['answer']}" for ex in previous_exchanges
            )
            user_content = (
                f"Job role: {job_role}.{tech_part} So far:\n\n{history}\n\n"
                "Ask the next interview question (one question only)."
            )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=256,
            )
            text = response.choices[0].message.content
            return (text or "").strip()
        except Exception as e:
            return f"[Error from OpenAI: {e!s}]"

    async def generate_agent_report(
        self,
        job_role: str,
        exchanges: list[dict],
        interrupt_count: int,
    ) -> dict | None:
        """
        Generate agent report: accuracy_score (0-100), communication_score (0-100), summary.
        Returns dict or None if OpenAI not configured.
        """
        if not self._client or not exchanges:
            return None
        history = "\n\n".join(
            f"Q: {ex['question']}\nA: {ex['answer']}" for ex in exchanges
        )
        system = (
            "You are an interview assessor. Based on the Q&A, output a JSON object with exactly these keys: "
            '"accuracy_score" (0-100, how correct/technical the answers were), '
            '"communication_score" (0-100, clarity and professionalism), '
            '"summary" (2-4 sentences for the admin). '
            "Reply with only the JSON, no other text."
        )
        user_content = (
            f"Job role: {job_role}. Interruptions (user cut agent): {interrupt_count}.\n\n"
            f"Interview:\n{history}\n\n"
            "Provide the JSON assessment."
        )
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=400,
            )
            text = (response.choices[0].message.content or "").strip()
            import json
            # Extract JSON if wrapped in markdown
            if "```" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    text = text[start:end]
            return json.loads(text)
        except Exception:
            return None
