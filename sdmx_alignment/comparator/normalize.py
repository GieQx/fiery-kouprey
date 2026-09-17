import re


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"[_\-]+", " ", value.casefold())
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())

