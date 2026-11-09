"""Hand-computed examples, invariants and invalid input coverage."""

import itertools

import pytest
from app.learner.bkt import bkt_update, label_for, params_for


@pytest.mark.parametrize(
    "correct,expected", [(True, 0.6460674157303371), (False, 0.14864864864864866)]
)
def test_hand_calculated_updates(correct, expected):
    assert bkt_update(0.3, correct, params_for()) == pytest.approx(expected)


def test_guess_rates():
    mc = bkt_update(0.3, True, params_for("multiple_choice"))
    short = bkt_update(0.3, True, params_for("short_answer"))
    assert short == pytest.approx(0.8967213114754098)
    assert short > mc
    assert params_for("short_answer", guess=0.2)["guess"] == 0.2


def test_prior_and_legacy_interface():
    params = params_for(prior=0.6)
    assert bkt_update(None, True, params) == bkt_update(0.6, True, params)
    assert bkt_update(0.3, True, params) == bkt_update(0.3, True, params_for())
    assert bkt_update(
        0.3, True, {"learn": 0.1, "guess": 0.25, "slip": 0.1}
    ) == bkt_update(0.3, True, params_for())
    assert bkt_update(
        None, True, {"learn": 0.1, "guess": 0.25, "slip": 0.1}
    ) == bkt_update(0.3, True, params_for())


def test_transition_once_and_after_observation():
    posterior = 0.27 / (0.27 + 0.175)
    assert bkt_update(0.3, True, params_for(learn=0)) == pytest.approx(posterior)
    assert bkt_update(0.3, True, params_for()) == pytest.approx(
        posterior + (1 - posterior) * 0.1
    )
    assert bkt_update(0.3, False, params_for(learn=1)) == 1


@pytest.mark.parametrize(
    "p,expected",
    [
        (0, "not_mastered"),
        (0.499999, "not_mastered"),
        (0.5, "confused"),
        (0.799999, "confused"),
        (0.8, "mastered"),
        (1, "mastered"),
    ],
)
def test_labels(p, expected):
    assert label_for(p) == expected


@pytest.mark.parametrize("p", [None, 0, 0.3, 1])
def test_untested(p):
    assert label_for(p, tested=False) == "untested"


BAD = [
    10**400,
    -0.01,
    1.01,
    float("nan"),
    float("inf"),
    -float("inf"),
    True,
    "0.3",
    [],
    None,
]


@pytest.mark.parametrize("bad", BAD)
def test_invalid_probability(bad):
    with pytest.raises(ValueError):
        label_for(bad)
    if bad is not None:
        with pytest.raises(ValueError):
            bkt_update(bad, True, params_for())
        with pytest.raises(ValueError):
            label_for(bad, tested=False)


@pytest.mark.parametrize(
    "field,bad", list(itertools.product(["prior", "learn", "guess", "slip"], BAD))
)
def test_invalid_params(field, bad):
    params = params_for()
    params[field] = bad
    with pytest.raises(ValueError):
        bkt_update(0.3, True, params)
    with pytest.raises(ValueError):
        params_for(**{field: bad})


@pytest.mark.parametrize("bad", [None, 0, 1, "false", []])
def test_boolean_inputs(bad):
    with pytest.raises(ValueError):
        bkt_update(0.3, bad, params_for())
    with pytest.raises(ValueError):
        label_for(0.3, tested=bad)


@pytest.mark.parametrize("params", [None, [], {}, {"guess": 0.2, "learn": 0.1}])
def test_missing_params(params):
    with pytest.raises(ValueError):
        bkt_update(0.3, True, params)


@pytest.mark.parametrize("question_type", ["essay", None, []])
def test_unknown_question_type(question_type):
    with pytest.raises(ValueError):
        params_for(question_type)


def test_parameter_factory_is_independent():
    params = params_for()
    params["guess"] = 0.9
    assert params_for()["guess"] == 0.25
    with pytest.raises(ValueError):
        params_for(learning=0.2)


@pytest.mark.parametrize(
    "p,learn,guess,slip,correct",
    list(
        itertools.product(
            [0, 0.3, 1], [0, 0.1, 1], [0, 0.25, 1], [0, 0.1, 1], [False, True]
        )
    ),
)
def test_probability_grid(p, learn, guess, slip, correct):
    likelihood = p * (1 - slip if correct else slip) + (1 - p) * (
        guess if correct else 1 - guess
    )
    params = dict(learn=learn, guess=guess, slip=slip)
    if likelihood == 0:
        with pytest.raises(ValueError, match="zero probability"):
            bkt_update(p, correct, params)
    else:
        assert 0 <= bkt_update(p, correct, params) <= 1


def test_no_learning_evidence_and_sequences():
    p = 0.3
    params = params_for(learn=0)
    assert bkt_update(p, True, params) > p > bkt_update(p, False, params)
    for _ in range(15):
        p = bkt_update(p, True, params_for())
    assert label_for(p) == "mastered"
    p = 0.3
    for _ in range(15):
        p = bkt_update(p, False, params_for())
    assert label_for(p) == "not_mastered"
