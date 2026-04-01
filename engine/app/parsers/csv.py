import csv
from io import StringIO


def parse_csv(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content)))
