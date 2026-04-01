try:
    from seed.entities import build_entities
    from seed.organizations import build_organizations
    from seed.patterns import build_patterns
    from seed.str_reports import build_str_reports
    from seed.transactions import build_transaction_count
except ModuleNotFoundError:
    from entities import build_entities
    from organizations import build_organizations
    from patterns import build_patterns
    from str_reports import build_str_reports
    from transactions import build_transaction_count


def build_seed_summary() -> dict[str, int]:
    return {
        "organizations": len(build_organizations()),
        "entities": len(build_entities()),
        "str_reports": len(build_str_reports()),
        "transactions": build_transaction_count(),
        "patterns": len(build_patterns()),
    }


if __name__ == "__main__":
    print(build_seed_summary())
