from __future__ import annotations

import re
from typing import Any


def safe_score(value: Any, default: int = 0) -> int:
    """Converte diferentes formatos de nota para um inteiro entre 0 e 100."""
    try:
        if isinstance(value, bool):
            return default

        if isinstance(value, (int, float)):
            return max(0, min(100, round(value)))

        text = str(value or "").strip()
        if not text:
            return default

        match = re.search(r"\b(100|\d{1,2})\b", text)
        if not match:
            return default

        return max(0, min(100, int(match.group(1))))
    except (TypeError, ValueError):
        return default


def safe_score_dict(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}

    return {
        str(key): safe_score(score)
        for key, score in value.items()
    }


def average_positive_scores(scores: dict[str, int], default: int = 0) -> int:
    valid = [score for score in scores.values() if score > 0]
    if not valid:
        return default
    return round(sum(valid) / len(valid))
