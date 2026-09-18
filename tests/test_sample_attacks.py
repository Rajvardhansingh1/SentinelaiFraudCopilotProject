from frontend.data.sample_attacks import SAMPLE_ATTACKS
from proxy.middleware.injection_detector import check_injection


def test_every_sample_attack_trips_a_real_pattern():
    for attack in SAMPLE_ATTACKS:
        result = check_injection(attack["prompt"])
        assert result.flagged is True, f"{attack['id']} did not trip any real attack pattern"


def test_cached_response_matched_patterns_are_subset_of_real_matches():
    for attack in SAMPLE_ATTACKS:
        result = check_injection(attack["prompt"])
        cached_patterns = set(attack["cached_response"]["guardrails"]["injection"]["matched_patterns"])
        assert cached_patterns.issubset(set(result.matched_patterns))
