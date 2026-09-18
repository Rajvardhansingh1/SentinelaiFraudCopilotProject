import re

ATTACK_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ignore_instructions", re.compile(r"ignore (all |any |previous |prior )*instructions", re.I)),
    ("role_override", re.compile(r"you are now|act as|pretend (to be|you are)|new persona", re.I)),
    ("system_prompt_leak", re.compile(r"reveal (your |the )?system prompt|show me your (instructions|prompt)", re.I)),
    ("dan_jailbreak", re.compile(r"\bDAN\b|do anything now", re.I)),
    ("policy_override", re.compile(r"ignore (policy|guardrails|safety)|approve (this|the) claim", re.I)),
    ("developer_mode", re.compile(r"developer mode|jailbreak", re.I)),
    ("encoded_payload", re.compile(r"base64:|\\x[0-9a-f]{2}", re.I)),
    ("prompt_extraction", re.compile(r"repeat (the )?(words |text )?above|print (your |the )?(prompt|instructions)", re.I)),
    ("delimiter_escape", re.compile(r"</?(system|instructions?)>|```system|---\s*end\s*(of\s*)?prompt", re.I)),
    ("hidden_text_marker", re.compile(r"\[hidden\]|invisible text|tiny text", re.I)),
]
