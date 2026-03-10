from typing import Any

def sanitize_null_bytes(data: Any) -> Any:
    if isinstance(data, str):
        return data.replace("\x00", "")
    elif isinstance(data, list):
        return [sanitize_null_bytes(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_null_bytes(value) for key, value in data.items()}
    else:
        return data
