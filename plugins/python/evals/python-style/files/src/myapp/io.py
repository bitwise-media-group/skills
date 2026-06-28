import os


def load_config(path):
    if not os.path.exists(path):
        print("config not found: " + path)
        return {}
    f = open(os.path.join(path, "config.txt"))
    data = f.read()
    f.close()
    try:
        return _parse(data)
    except Exception:
        print("could not parse config")
        return {}


def _parse(data):
    result = {}
    for line in data.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result
