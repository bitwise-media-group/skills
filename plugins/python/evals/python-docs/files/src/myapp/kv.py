def parse(line: str) -> tuple[str, str]:
    if "=" not in line:
        raise ValueError("missing separator")
    key, value = line.split("=", 1)
    if not key.strip():
        raise ValueError("empty key")
    return key.strip(), value.strip()


def format_pair(key: str, value: str) -> str:
    return f"{key}={value}"
