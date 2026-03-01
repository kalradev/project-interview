"""
AI Text Detector - extracts features and returns AI probability (0-1).

Features: sentence length, vocabulary richness, perplexity, burstiness.
Uses pre-trained classifier (ai_classifier.pkl) when available.
"""

from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import get_settings


class AITextDetector:
    """
    Detects likelihood that text was AI-generated.
    Returns ai_probability in [0, 1].
    """

    def __init__(self, classifier_path: Optional[str] = None):
        self.settings = get_settings()
        self.path = Path(classifier_path or self.settings.ai_classifier_path)
        self._classifier = None
        self._vectorizer = None
        self._load_classifier()

    def _load_classifier(self) -> None:
        """Load pre-trained classifier and vectorizer from disk."""
        if not self.path.exists():
            return
        try:
            import joblib
            data = joblib.load(self.path)
            if isinstance(data, dict):
                self._classifier = data.get("classifier")
                self._vectorizer = data.get("vectorizer")
            else:
                self._classifier = data
        except Exception:
            self._classifier = None
            self._vectorizer = None

    def _sentence_length_features(self, text: str) -> list[float]:
        """Average and std of sentence lengths (words)."""
        if not text.strip():
            return [0.0, 0.0]
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if not sentences:
            return [0.0, 0.0]
        lengths = [len(s.split()) for s in sentences]
        return [float(np.mean(lengths)), float(np.std(lengths)) if len(lengths) > 1 else 0.0]

    def _vocabulary_richness(self, text: str) -> float:
        """Unique words / total words ratio."""
        words = text.lower().split()
        if not words:
            return 0.0
        return len(set(words)) / len(words)

    def _perplexity_proxy(self, text: str) -> float:
        """Simple proxy: inverse of avg word length (longer words => lower proxy)."""
        words = text.split()
        if not words:
            return 0.0
        avg_len = np.mean([len(w) for w in words])
        return 1.0 / (avg_len + 1e-6)

    def _burstiness(self, text: str) -> float:
        """Burstiness: variance of sentence lengths relative to mean."""
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if len(sentences) < 2:
            return 0.0
        lengths = [len(s.split()) for s in sentences]
        mean_l = np.mean(lengths)
        std_l = np.std(lengths)
        if mean_l == 0:
            return 0.0
        return float(std_l / (mean_l + 1e-6))

    def extract_features(self, text: str) -> dict[str, float]:
        """Extract all features for a text string."""
        sen_mean, sen_std = self._sentence_length_features(text)
        return {
            "sentence_length_mean": sen_mean,
            "sentence_length_std": sen_std,
            "vocabulary_richness": self._vocabulary_richness(text),
            "perplexity_proxy": self._perplexity_proxy(text),
            "burstiness": self._burstiness(text),
            "word_count": float(len(text.split())),
        }

    def feature_vector(self, text: str) -> np.ndarray:
        """Numeric feature vector for classifier (order must match training)."""
        f = self.extract_features(text)
        return np.array([
            f["sentence_length_mean"],
            f["sentence_length_std"],
            f["vocabulary_richness"],
            f["perplexity_proxy"],
            f["burstiness"],
            f["word_count"],
        ], dtype=np.float64).reshape(1, -1)

    def predict_proba(self, text: str) -> float:
        """
        Return AI probability in [0, 1].
        Uses pre-trained classifier if available; else heuristic.
        """
        if not text or not text.strip():
            return 0.0
        features = self.extract_features(text)
        if self._classifier is not None:
            try:
                X = self.feature_vector(text)
                proba = self._classifier.predict_proba(X)
                # Assume class 1 is "AI"
                if proba.shape[1] == 2:
                    return float(proba[0, 1])
                return float(proba[0, 0])
            except Exception:
                pass
        # Heuristic fallback: higher burstiness + higher sentence length => higher AI likelihood
        ai_score = 0.0
        ai_score += min(1.0, features["sentence_length_mean"] / 25) * 0.3
        ai_score += min(1.0, features["burstiness"]) * 0.3
        ai_score += (1.0 - features["vocabulary_richness"]) * 0.4
        return float(np.clip(ai_score, 0.0, 1.0))

    def is_loaded(self) -> bool:
        """Whether a pre-trained classifier is loaded."""
        return self._classifier is not None
