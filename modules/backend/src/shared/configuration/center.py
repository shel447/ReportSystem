from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Generic, Mapping, Protocol, TypeVar

T = TypeVar("T")


class ConfigSource(Protocol):
    name: str

    def load(self) -> Mapping[str, Mapping[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class ConfigKey(Generic[T]):
    name: str
    parser: Callable[[Mapping[str, Any]], T]
    required: bool = False


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    values: Mapping[str, object]
    sources: Mapping[str, Mapping[str, str]]
    failures: tuple[str, ...] = ()


class ConfigCenter:
    def __init__(self, *, keys: tuple[ConfigKey[Any], ...]) -> None:
        self._keys = {key.name: key for key in keys}
        self._snapshot: ConfigSnapshot | None = None

    def initialize(self, sources: tuple[ConfigSource, ...]) -> ConfigSnapshot:
        merged: dict[str, dict[str, Any]] = {name: {} for name in self._keys}
        provenance: dict[str, dict[str, str]] = {name: {} for name in self._keys}
        failures: list[str] = []
        for source in sources:
            try:
                payload = source.load()
            except Exception as exc:
                failures.append(f"{source.name}: {exc}")
                continue
            for name, patch in payload.items():
                if name not in self._keys or not isinstance(patch, Mapping):
                    continue
                _deep_merge(merged[name], patch, provenance[name], source.name)

        values: dict[str, object] = {}
        errors: list[str] = []
        for name, key in self._keys.items():
            try:
                values[name] = key.parser(merged[name])
            except Exception as exc:
                if key.required:
                    errors.append(f"{name}: {exc}")
                else:
                    failures.append(f"{name}: {exc}")
        if errors:
            raise ValueError("invalid ChatBI configuration: " + "; ".join(errors))
        self._snapshot = ConfigSnapshot(
            values=MappingProxyType(values),
            sources=MappingProxyType(
                {name: MappingProxyType(dict(fields)) for name, fields in provenance.items()}
            ),
            failures=tuple(failures),
        )
        return self._snapshot

    def get(self, key: ConfigKey[T]) -> T:
        if self._snapshot is None:
            raise RuntimeError("ConfigCenter is not initialized")
        return self._snapshot.values[key.name]  # type: ignore[return-value]

    def snapshot(self) -> ConfigSnapshot:
        if self._snapshot is None:
            raise RuntimeError("ConfigCenter is not initialized")
        return self._snapshot

    def reset(self) -> None:
        self._snapshot = None


def _deep_merge(
    target: dict[str, Any],
    patch: Mapping[str, Any],
    provenance: dict[str, str],
    source_name: str,
    *,
    prefix: str = "",
) -> None:
    for key, raw_value in patch.items():
        field_path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(raw_value, Mapping):
            child = target.setdefault(str(key), {})
            if not isinstance(child, dict):
                child = {}
                target[str(key)] = child
            _deep_merge(child, raw_value, provenance, source_name, prefix=field_path)
            continue
        target[str(key)] = deepcopy(raw_value)
        provenance[field_path] = source_name
