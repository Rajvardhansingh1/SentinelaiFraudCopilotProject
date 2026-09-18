from agents.proxy_client import ProxyCallFailed, call_proxy

EXTRACTOR_SYSTEM_PROMPT = (
    "Extract vendor, date, line_items, and total from the receipt text below. "
    "Respond with JSON matching this shape exactly: "
    '{"vendor": str|null, "date": str|null, "line_items": [str], "total": float|null}.'
)


class OcrError(Exception):
    pass


def run_ocr(image_path: str) -> str:
    """Local RapidOCR pass (D-014). Never returns an empty string silently on failure."""
    try:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()
        result, _ = engine(image_path)
    except Exception as exc:
        raise OcrError(f"OCR failed for {image_path}: {exc}") from exc
    if not result:
        raise OcrError(f"OCR produced no text for {image_path}")
    return "\n".join(line[1] for line in result)


def extract_fields(session_id: str, ocr_text: str) -> tuple[dict | None, dict | None, dict | None]:
    """Returns (extracted_fields, guardrails, error). Exactly one of the first two is None on failure."""
    try:
        status_code, body = call_proxy(
            session_id=session_id,
            operation="extract",
            messages=[
                {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
                {"role": "user", "content": ocr_text},
            ],
            schema_name="receipt_fields",
        )
    except ProxyCallFailed as exc:
        return None, None, {"node": "extractor", "code": "proxy_unreachable", "message": str(exc)}

    if status_code != 200:
        error = body.get("error") or {"code": "unknown", "message": "extract call failed"}
        return None, body.get("guardrails"), {"node": "extractor", "code": error["code"], "message": error["message"]}

    return body["output"], body["guardrails"], None
