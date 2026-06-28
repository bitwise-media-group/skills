def parse(line: str) -> tuple[str, str]:
    if "=" not in line:
        raise ValueError("missing separator")
    key, value = line.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError("empty key")
    return key, value.strip()
