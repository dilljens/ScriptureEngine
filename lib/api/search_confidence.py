"""
BLIM confidence scoring for search results.

Applies the existing BLIM (2PL IRT) model from lib/assessment/models.py
to search results — providing per-result calibrated confidence scores (0-100).

The same BLIM model used for assessment items is now used for search,
giving users a calibrated signal of result reliability.

Port from uki's wrappers/confidence.py, which itself was ported from
ScriptureEngine's lib/assessment/models.py.
"""

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

_SEARCH_CONF_DIR = Path.home() / ".local" / "state" / "clew"


# ── BLIM Model (ported from assessment/models.py for search) ─────────

class BLIM:
    """Basic Local Independence Model (2PL IRT) for search result calibration.
    
    Each query-result pair has:
      - difficulty (beta): higher = harder to judge relevance
      - discrimination (alpha): how well relevance signals separate good from bad
      - guess (g): P(high score | not actually relevant)
      - slip (s): P(low score | actually relevant)
    """

    def __init__(self, difficulty=0.0, discrimination=1.0, guess=0.15, slip=0.10):
        self.difficulty = difficulty
        self.discrimination = discrimination
        self.guess = guess
        self.slip = slip

    def p_relevant(self, ability: float) -> float:
        """2PL IRT: P(relevant) = guess + (1-guess-slip) * logistic(alpha(theta-beta))."""
        logit = self.discrimination * (ability - self.difficulty)
        try:
            p = 1.0 / (1.0 + math.exp(-logit))
        except OverflowError:
            p = 1.0 if logit > 0 else 0.0
        return self.guess + (1.0 - self.guess - self.slip) * p

    def update_bayesian(self, prior: float, feedback_correct: bool, correctness: float = 1.0) -> float:
        """Bayesian update of confidence after feedback."""
        p_correct_given_rel = 1.0 - self.slip
        p_correct_given_not = self.guess
        if feedback_correct:
            p_evidence = p_correct_given_rel * prior + p_correct_given_not * (1.0 - prior)
            if p_evidence <= 0:
                return prior
            posterior = (p_correct_given_rel * prior) / p_evidence
        else:
            p_wrong = self.slip * prior + (1.0 - self.guess) * (1.0 - prior)
            if p_wrong <= 0:
                return prior
            posterior = self.slip * prior / p_wrong
        return posterior * correctness + prior * (1.0 - correctness)


# ── Query ability estimation ────────────────────────────────────────

def _query_ability(query: str) -> float:
    """Estimate query clarity/specificity as theta for the IRT model.
    
    Longer queries, codes, versions, and quoted phrases → higher ability.
    """
    q = query.strip()
    if not q:
        return 0.0

    word_count = len(q.split())
    length_score = min(word_count / 10.0, 1.0) * 0.3
    has_code = bool(re.search(r'[A-Z]{2,6}[-_]\d{2,}', q))
    has_version = bool(re.search(r'\d+\.\d+\.?\d*', q))
    has_quotes = q.count('"') >= 2
    specificity = 0.2 if has_code or has_version or has_quotes else 0.0
    is_question = any(q.lower().startswith(w) for w in ("what", "how", "why", "when", "where", "which"))
    question_bonus = 0.1 if is_question else 0.0
    return min(1.0, 0.3 + length_score + specificity + question_bonus)


# ── Knowledge state persistence ─────────────────────────────────────

class KnowledgeState:
    """Tracks per-query-pattern confidence across sessions.
    
    Persisted to JSON file for calibration data survival.
    """

    def __init__(self):
        self._state: dict[str, dict] = {}
        self._state_path: Path = _SEARCH_CONF_DIR / "search_confidence_state.json"
        self._load()
        self._blims: dict[str, BLIM] = {}

    def _load(self):
        if self._state_path.exists():
            try:
                self._state = json.loads(self._state_path.read_text())
            except (json.JSONDecodeError, OSError):
                self._state = {}

    def _save(self):
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(self._state, indent=2))
        except OSError:
            pass

    def get(self, query_key: str) -> dict:
        return self._state.get(query_key, {"confidence": 0.5, "observations": 0, "last_seen": None})

    def update(self, query_key: str, confidence: float, observation_count: int = 1):
        current = self.get(query_key)
        total = current["observations"] + observation_count
        alpha = observation_count / total if total > 0 else 1.0
        new_confidence = (1.0 - alpha) * current["confidence"] + alpha * confidence
        self._state[query_key] = {
            "confidence": round(new_confidence, 4),
            "observations": total,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
        self._save()


# ── Module-level singleton ──────────────────────────────────────────

_STATE = KnowledgeState()


def _get_blim(query_key: str) -> BLIM:
    """Get or create a BLIM model for a query pattern."""
    if query_key not in _STATE._blims:
        _STATE._blims[query_key] = BLIM()
    return _STATE._blims[query_key]


# ── Public API ──────────────────────────────────────────────────────

def score_result(query: str, result: dict) -> dict:
    """Wrap a search result with a BLIM-calibrated confidence score (0-100).
    
    Args:
        query: The search query.
        result: The result dict (must have at least 'verse' or 'doc_id').
    
    Returns:
        Result dict with added 'confidence_score' (0-100) and '_blim_info' fields.
    """
    ability = _query_ability(query)
    doc_id = result.get("verse") or result.get("doc_id", "") or result.get("id", "")
    query_key = f"{query.strip().lower()}:{doc_id}"

    prior = _STATE.get(query_key)
    blim = _get_blim(query_key)
    confidence = blim.p_relevant(ability)

    if prior["observations"] > 0:
        alpha = min(prior["observations"] / (prior["observations"] + 5), 0.7)
        confidence = (1.0 - alpha) * confidence + alpha * prior["confidence"]

    result = dict(result)
    result["confidence_score"] = round(confidence * 100)
    result["_blim_info"] = {
        "ability": round(ability, 3),
        "observations": prior["observations"],
    }
    return result


def update_from_feedback(query: str, doc_id: str, was_relevant: bool, correctness: float = 1.0):
    """Calibrate the BLIM model from user feedback.
    
    Args:
        query: The original search query.
        doc_id: The document/verse ID the user interacted with.
        was_relevant: Whether the user found it relevant.
        correctness: Partial credit for nuanced feedback.
    """
    query_key = f"{query.strip().lower()}:{doc_id}"
    blim = _get_blim(query_key)
    prior = _STATE.get(query_key)
    posterior = blim.update_bayesian(prior["confidence"] or 0.5, was_relevant, correctness)
    _STATE.update(query_key, posterior)
