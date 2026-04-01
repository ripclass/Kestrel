def score_results(results: list[dict[str, object]]) -> int:
    if not results:
        return 0
    return min(100, int(sum(item["score"] for item in results) / len(results)))
