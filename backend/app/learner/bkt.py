def bkt_update(p, correct, params):
    """
    Update a student's mastery probability using BKT.
    """

    learn = params["learn"]
    guess = params["guess"]
    slip = params["slip"]

    if correct:
        numerator = p * (1 - slip)
        denominator = numerator + (1 - p) * guess
    else:
        numerator = p * slip
        denominator = numerator + (1 - p) * (1 - guess)

    if denominator == 0:
        raise ValueError("This answer has zero probability.")

    posterior = numerator / denominator

    new_p = posterior + (1 - posterior) * learn

    return new_p
