from pydantic import BaseModel, ValidationError


def validate_structured_output(model: type[BaseModel], payload: object) -> tuple[bool, str | None]:
    try:
        model.model_validate(payload)
    except ValidationError as exc:
        return False, str(exc)
    return True, None
