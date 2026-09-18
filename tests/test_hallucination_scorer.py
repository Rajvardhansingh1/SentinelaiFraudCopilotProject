from proxy.eval.hallucination_scorer import score_grounded, score_ungrounded


def test_grounded_fully_supported():
    context = "Vendor is Acme Corp. Total is 42.50. Purchased on 2026-01-01."
    response = "The vendor is Acme Corp. The total is 42.50."
    result = score_grounded(response, context)
    assert result.mode == "grounded"
    assert result.score == 0.0


def test_grounded_fully_unsupported():
    context = "Vendor is Acme Corp. Total is 42.50."
    response = "The spaceship launched to Mars yesterday."
    result = score_grounded(response, context)
    assert result.score == 1.0


def test_grounded_partial_support():
    context = "Vendor is Acme Corp. Total is 42.50."
    response = "The vendor is Acme Corp. The spaceship launched to Mars."
    result = score_grounded(response, context)
    assert 0.0 < result.score < 1.0


def test_grounded_empty_response():
    result = score_grounded("", "some context")
    assert result.score == 0.0


def test_ungrounded_identical_samples_low_score():
    samples = ["the total is 42.50", "the total is 42.50"]
    result = score_ungrounded(samples)
    assert result.mode == "ungrounded"
    assert result.score == 0.0


def test_ungrounded_divergent_samples_high_score():
    samples = ["the total is 42.50", "aliens built the pyramids"]
    result = score_ungrounded(samples)
    assert result.score > 0.5


def test_ungrounded_single_sample_returns_zero():
    result = score_ungrounded(["only one sample"])
    assert result.score == 0.0
