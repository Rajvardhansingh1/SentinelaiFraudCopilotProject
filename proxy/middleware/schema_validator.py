from typing import Callable

from pydantic import BaseModel, ValidationError

from proxy.schemas import SCHEMA_REGISTRY


class SchemaValidationFailed(Exception):
    pass


def validate_structured_output(
    schema_name: str,
    raw_output_getter: Callable[[], str],
) -> tuple[BaseModel, bool]:
    """Validate raw JSON text against schema_name. Retries the getter once on failure.

    Returns (validated_model, retried).
    """
    model_cls = SCHEMA_REGISTRY[schema_name]
    retried = False
    for attempt in range(2):
        raw = raw_output_getter()
        try:
            return model_cls.model_validate_json(raw), retried
        except ValidationError:
            if attempt == 0:
                retried = True
                continue
    raise SchemaValidationFailed(f"invalid output for schema '{schema_name}' after retry")
