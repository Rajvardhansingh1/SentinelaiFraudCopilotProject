from proxy.redteam.attack_library import ATTACK_PATTERNS
from proxy.schemas import InjectionResult


def check_injection(text: str) -> InjectionResult:
    matched = [name for name, pattern in ATTACK_PATTERNS if pattern.search(text)]
    return InjectionResult(flagged=bool(matched), matched_patterns=matched)
