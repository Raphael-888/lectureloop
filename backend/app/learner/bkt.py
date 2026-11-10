"""Binary BKT without forgetting; defaults are experimental, not calibrated."""

from collections.abc import Mapping
from math import isfinite
from numbers import Real

MASTERY_THRESHOLD = 0.8
CONFUSED_THRESHOLD = 0.5


def _probability(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number between 0 and 1")
    if not 0 <= value <= 1 or not isfinite(value):
        raise ValueError(f"{name} must be a finite number between 0 and 1")
    return float(value)


def params_for(question_type="multiple_choice", **overrides):
    """Return fresh MVP parameters; callers can override every probability."""
    guesses = {"multiple_choice": 0.25, "short_answer": 0.05}
    if not isinstance(question_type, str) or question_type not in guesses:
        raise ValueError("Unknown question type")
    if overrides.keys() - {"prior", "learn", "guess", "slip"}:
        raise ValueError("Unknown BKT parameter")
    params = dict(prior=0.30, learn=0.10, guess=guesses[question_type], slip=0.10)
    params.update(overrides)
    return {key: _probability(value, key) for key, value in params.items()}


def bkt_update(p, correct, params):
    """Condition on an answer, then apply ONE learning transition.

    Preserves original timing: posterior + (1 - posterior) * learn.
    B must not apply a second transition after explanation unless agreed.
    Explicit p takes precedence over params['prior']; p=None initializes from
    that prior (default 0.30). Existing three-argument calls remain valid.
    Zero-likelihood answers raise ValueError rather than fabricate evidence.
    """
    if not isinstance(params, Mapping):
        raise ValueError("params must be a mapping")
    if type(correct) is not bool:
        raise ValueError("correct must be a boolean")
    missing = {"learn", "guess", "slip"} - params.keys()
    if missing:
        raise ValueError(f"Missing BKT parameters: {', '.join(sorted(missing))}")
    prior = _probability(params.get("prior", 0.30), "prior")
    p = _probability(prior if p is None else p, "p")
    learn, guess, slip = (
        _probability(params[key], key) for key in ("learn", "guess", "slip")
    )
    numerator = p * (1 - slip if correct else slip)
    other = (1 - p) * (guess if correct else 1 - guess)
    denominator = numerator + other
    if denominator == 0:
        raise ValueError("This answer has zero probability.")
    posterior = numerator / denominator
    return posterior + (1 - posterior) * learn


def label_for(p, tested=True):
    """Untested status comes from answer history, never from a low prior."""
    if type(tested) is not bool:
        raise ValueError("tested must be a boolean")
    if p is not None or tested:
        p = _probability(p, "p")
    if not tested:
        return "untested"
    if p >= MASTERY_THRESHOLD:
        return "mastered"
    if p >= CONFUSED_THRESHOLD:
        return "confused"
    return "not_mastered"
