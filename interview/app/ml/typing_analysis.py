"""
Typing analysis - words per second, burst typing, instant large input detection.

Uses keystroke timestamps to compute:
- Typing speed (words per second)
- Burst typing (unnaturally fast segments)
- Instant large input (copy-paste behavior)
"""

from typing import Optional


def words_per_second(keystroke_timestamps: list[float], word_count: int) -> Optional[float]:
    """
    Compute typing speed as words per second.
    word_count should be derived from the final text length (e.g. len(text.split())).
    """
    if not keystroke_timestamps or word_count <= 0:
        return None
        # If we only have text length, use last - first as duration
    timestamps = sorted(keystroke_timestamps)
    duration_sec = timestamps[-1] - timestamps[0]
    if duration_sec <= 0:
        return None
    return word_count / duration_sec


def detect_burst_typing(
    keystroke_timestamps: list[float],
    threshold_interval_sec: float = 0.05,
    min_burst_size: int = 5,
) -> bool:
    """
    Detect burst typing: many keystrokes in very short intervals.
    Returns True if burst behavior is detected.
    """
    if len(keystroke_timestamps) < min_burst_size:
        return False
    timestamps = sorted(keystroke_timestamps)
    for i in range(len(timestamps) - min_burst_size + 1):
        window = timestamps[i : i + min_burst_size]
        span = window[-1] - window[0]
        if span <= threshold_interval_sec and span >= 0:
            return True
    return False


def detect_instant_large_input(
    keystroke_timestamps: list[float],
    text_length: int,
    min_chars: int = 50,
    max_interval_sec: float = 0.5,
) -> bool:
    """
    Detect instant large input (e.g. paste): many characters appearing in a very short time.
    Returns True if behavior suggests copy-paste.
    """
    if text_length < min_chars or len(keystroke_timestamps) < 2:
        return False
    timestamps = sorted(keystroke_timestamps)
    span = timestamps[-1] - timestamps[0]
    if span <= max_interval_sec and text_length >= min_chars:
        return True
    return False
