"""
ModelRegistry — discovers, loads, and caches all 55 model instances.

Usage:
  from app.ml.registry import register_model, get_registry

  @register_model("M-A1")
  class MarketSizingModel(BaseMLModel): ...

  registry = get_registry()
  model = registry.get("M-A1")
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Type

from app.ml.base import BaseMLModel, ModelMetadata

# ─── Global model class registry ──────────────────────────────────────────────
_CLASS_REGISTRY: dict[str, Type[BaseMLModel]] = {}


def register_model(model_id: str):
    """Decorator that registers a BaseMLModel subclass by its model_id."""

    def decorator(cls: Type[BaseMLModel]) -> Type[BaseMLModel]:
        _CLASS_REGISTRY[model_id] = cls
        return cls

    return decorator


# ─── Auto-import all block submodules ─────────────────────────────────────────

def _autodiscover() -> None:
    """
    Walk every ml/block_* package and import all modules.
    The @register_model decorators fire on import, populating _CLASS_REGISTRY.
    """
    import app.ml.block_a as _ba
    import app.ml.block_b as _bb
    import app.ml.block_c as _bc
    import app.ml.block_d as _bd
    import app.ml.block_e as _be
    import app.ml.block_f as _bf
    import app.ml.block_g as _bg
    import app.ml.block_h as _bh
    import app.ml.block_i as _bi
    import app.ml.block_j as _bj

    for pkg in (_ba, _bb, _bc, _bd, _be, _bf, _bg, _bh, _bi, _bj):
        for _finder, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg.__name__}.{modname}")


# ─── Registry class ────────────────────────────────────────────────────────────

class ModelRegistry:
    """
    Singleton-like registry that holds one loaded instance per (model_id, version).
    Instances are cached in-process; Redis is used for prediction output caching
    (handled in PredictionService, not here).
    """

    def __init__(self) -> None:
        _autodiscover()
        self._instances: dict[str, BaseMLModel] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, model_id: str, version: str = "latest") -> BaseMLModel:
        """Return a loaded model instance (cached after first load)."""
        if model_id not in _CLASS_REGISTRY:
            raise KeyError(f"Model '{model_id}' not found. Registered: {self.all_ids()}")

        cache_key = f"{model_id}:{version}"
        if cache_key not in self._instances:
            cls = _CLASS_REGISTRY[model_id]
            self._instances[cache_key] = cls.load(version)

        return self._instances[cache_key]

    def list_all(self) -> list[ModelMetadata]:
        """Return metadata for all registered models (instantiates once each)."""
        return [self.get(mid).get_metadata() for mid in sorted(_CLASS_REGISTRY)]

    def all_ids(self) -> list[str]:
        return sorted(_CLASS_REGISTRY.keys())

    def invalidate(self, model_id: str, version: str = "latest") -> None:
        """Drop a cached instance so the next get() reloads from MLflow."""
        cache_key = f"{model_id}:{version}"
        self._instances.pop(cache_key, None)

    def __len__(self) -> int:
        return len(_CLASS_REGISTRY)


# ─── Module-level singleton ────────────────────────────────────────────────────
_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
