from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


class NoDuplicateKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping_no_duplicates(loader: yaml.Loader, node: yaml.Node, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise AssertionError(f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


NoDuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_duplicates,
)


def test_runtime_yaml_files_have_no_duplicate_keys() -> None:
    for path in [
        REPO_ROOT / "agents" / "runtime.local.yaml",
        REPO_ROOT / "agents" / "runtime.local.example.yaml",
    ]:
        yaml.load(path.read_text(encoding="utf-8"), Loader=NoDuplicateKeyLoader)
