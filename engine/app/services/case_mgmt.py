from seed.fixtures import CASES


def list_cases() -> list[dict[str, object]]:
    return [case.model_dump(exclude={"timeline", "evidence_entities", "notes"}) for case in CASES]


def get_case_workspace(case_id: str) -> dict[str, object]:
    for case in CASES:
        if case.id == case_id:
            return case.model_dump()
    return CASES[0].model_dump()
