"""Answer analysis service - typing metrics and AI detection per answer."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.ai_text_detector import AITextDetector
from app.ml.typing_analysis import (
    words_per_second,
    detect_burst_typing,
    detect_instant_large_input,
)
from app.models.answer_analysis import AnswerAnalysis
from app.models.suspicious_event import EventType
from app.schemas.events import TypingEventRequest


class AnswerAnalysisService:
    """Analyze answer text and keystrokes; optionally log burst/instant events."""

    def __init__(self) -> None:
        self.ai_detector = AITextDetector()

    def analyze_typing(
        self,
        keystroke_timestamps: list[float],
        text_length: int,
        word_count: int,
    ) -> dict:
        """Compute WPS, burst, instant large input."""
        wps = words_per_second(keystroke_timestamps, word_count)
        burst = detect_burst_typing(keystroke_timestamps)
        instant = detect_instant_large_input(keystroke_timestamps, text_length)
        return {
            "words_per_second": wps,
            "burst_typing_detected": burst,
            "instant_large_input_detected": instant,
        }

    def analyze_text(self, text: str) -> dict:
        """Extract features and AI probability."""
        features = self.ai_detector.extract_features(text)
        ai_prob = self.ai_detector.predict_proba(text)
        return {"features": features, "ai_probability": ai_prob}

    async def create_analysis(
        self,
        db: AsyncSession,
        session_id: UUID,
        answer_text: str | None,
        keystroke_timestamps: list[float] | None,
        question_id: str | None,
        event_service=None,
    ) -> AnswerAnalysis:
        """Create AnswerAnalysis record; log burst/instant as events if event_service provided."""
        word_count = len(answer_text.split()) if answer_text else 0
        text_len = len(answer_text or "")
        wps = None
        ai_prob = None
        features = None
        if answer_text:
            out = self.analyze_text(answer_text)
            features = out["features"]
            ai_prob = out["ai_probability"]
        if keystroke_timestamps:
            typing = self.analyze_typing(keystroke_timestamps, text_len, word_count)
            wps = typing["words_per_second"]
            if event_service and typing.get("burst_typing_detected"):
                from app.schemas.events import EventLogRequest
                await event_service.log_event(
                    db,
                    EventLogRequest(
                        session_id=session_id,
                        event_type=EventType.BURST_TYPING,
                        payload=typing,
                    ),
                )
            if event_service and typing.get("instant_large_input_detected"):
                from app.schemas.events import EventLogRequest
                await event_service.log_event(
                    db,
                    EventLogRequest(
                        session_id=session_id,
                        event_type=EventType.INSTANT_LARGE_INPUT,
                        payload=typing,
                    ),
                )
        analysis = AnswerAnalysis(
            session_id=session_id,
            question_id=question_id,
            answer_text=answer_text,
            words_per_second=wps,
            ai_probability=ai_prob,
            features=features,
        )
        db.add(analysis)
        await db.flush()
        await db.refresh(analysis)
        return analysis
