from typing import Dict, List, Optional, Union


def lookup(key: str, table: Dict[str, int]) -> Optional[int]:
    return table.get(key)


def merge(a: List[int], b: List[int]) -> List[int]:
    return a + b


def coerce(x: Union[int, str]) -> str:
    return str(x)
