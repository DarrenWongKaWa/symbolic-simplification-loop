from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import resources

import jsonschema

from .config import REPO_ROOT, read_json


def schema_path(name: str) -> Path:
    if not name.endswith(".schema.json"):
        name = f"{name}.schema.json"
    candidates = [
        REPO_ROOT / "schemas" / name,
        Path(__file__).resolve().parents[1] / "schemas" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    try:
        with resources.as_file(resources.files("schemas").joinpath(name)) as resource_path:
            if resource_path.exists():
                return resource_path
    except (FileNotFoundError, ModuleNotFoundError):
        pass
    return candidates[0]


def validate_with_schema(data: dict[str, Any], schema_name: str) -> None:
    schema = read_json(schema_path(schema_name))
    jsonschema.validate(instance=data, schema=schema)


def load_and_validate(path: Path, schema_name: str) -> dict[str, Any]:
    data = read_json(path)
    validate_with_schema(data, schema_name)
    return data
