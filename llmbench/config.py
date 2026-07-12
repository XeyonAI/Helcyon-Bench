from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when config.yaml is missing or invalid."""


@dataclass
class JudgeEndpointConfig:
    name: str
    base_url: str
    api_key: str
    model: str
    local_endpoint_mode: str = "external"
    bench_lock_url: str = ""
    bench_unlock_url: str = ""
    temperature: float = 0.0
    max_tokens: int = 1200
    max_completion_tokens: int | None = None
    models: list[str] | None = None


@dataclass
class JudgeConfig(JudgeEndpointConfig):
    endpoints: list[JudgeEndpointConfig] | None = None


@dataclass
class AppConfig:
    judge: JudgeConfig
    debug_logging: bool = True


def load_config(app_dir: Path) -> AppConfig:
    path = app_dir / "config.yaml"
    if not path.exists():
        raise ConfigError("config.yaml was not found.")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    judge = raw.get("judge")
    if not isinstance(judge, dict):
        raise ConfigError("config.yaml must contain a judge section.")

    endpoints = load_judge_endpoints(judge)
    default_endpoint = endpoint_default(judge, endpoints)

    return AppConfig(
        judge=JudgeConfig(
            name=default_endpoint.name,
            base_url=default_endpoint.base_url,
            api_key=default_endpoint.api_key,
            model=default_endpoint.model,
            local_endpoint_mode=default_endpoint.local_endpoint_mode,
            bench_lock_url=default_endpoint.bench_lock_url,
            bench_unlock_url=default_endpoint.bench_unlock_url,
            temperature=default_endpoint.temperature,
            max_tokens=default_endpoint.max_tokens,
            max_completion_tokens=default_endpoint.max_completion_tokens,
            models=default_endpoint.models,
            endpoints=endpoints,
        ),
        debug_logging=bool(judge.get("debug_logging", True)),
    )


def load_judge_endpoint(name: str, raw: dict[str, Any]) -> JudgeEndpointConfig:
    required = ["base_url", "api_key", "model"]
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ConfigError(f"config.yaml is missing judge.{', judge.'.join(missing)}.")

    models = raw.get("models")
    if models is None:
        models = [raw["model"]]
    elif not isinstance(models, list) or not all(isinstance(item, str) for item in models):
        raise ConfigError("judge.models must be a list of model names.")

    return JudgeEndpointConfig(
        name=str(raw.get("name") or name),
        base_url=str(raw["base_url"]).rstrip("/"),
        api_key=str(raw["api_key"]),
        model=str(raw["model"]),
        local_endpoint_mode=str(raw.get("local_endpoint_mode") or "external"),
        bench_lock_url=str(raw.get("bench_lock_url") or ""),
        bench_unlock_url=str(raw.get("bench_unlock_url") or ""),
        temperature=float(raw.get("temperature", 0.0)),
        max_tokens=int(raw.get("max_tokens", 1200)),
        max_completion_tokens=(
            int(raw["max_completion_tokens"])
            if raw.get("max_completion_tokens") is not None
            else None
        ),
        models=models,
    )


def load_judge_endpoints(judge: dict[str, Any]) -> list[JudgeEndpointConfig]:
    raw_endpoints = judge.get("endpoints")
    if raw_endpoints is None:
        return [load_judge_endpoint("Default", judge)]

    endpoints = []
    if isinstance(raw_endpoints, dict):
        endpoint_items = raw_endpoints.items()
    elif isinstance(raw_endpoints, list):
        endpoint_items = [
            (str(item.get("name") or f"Endpoint {index}"), item)
            for index, item in enumerate(raw_endpoints, start=1)
            if isinstance(item, dict)
        ]
    else:
        raise ConfigError("judge.endpoints must be a mapping or list.")

    for name, endpoint in endpoint_items:
        if not isinstance(endpoint, dict):
            raise ConfigError("Each judge endpoint must be an object.")
        merged = {
            "api_key": judge.get("api_key"),
            "temperature": judge.get("temperature", 0.0),
            "max_tokens": judge.get("max_tokens", 1200),
            "max_completion_tokens": judge.get("max_completion_tokens"),
        } | endpoint
        endpoints.append(load_judge_endpoint(str(name), merged))

    if not endpoints:
        raise ConfigError("judge.endpoints must contain at least one endpoint.")
    return endpoints


def endpoint_default(judge: dict[str, Any], endpoints: list[JudgeEndpointConfig]) -> JudgeEndpointConfig:
    default_name = str(judge.get("default_endpoint") or "").strip()
    if default_name:
        for endpoint in endpoints:
            if endpoint.name == default_name:
                return endpoint
        raise ConfigError(f"judge.default_endpoint does not match a configured endpoint: {default_name}")
    return endpoints[0]


def judge_endpoint_by_name(config: JudgeConfig, name: str | None) -> JudgeEndpointConfig:
    endpoints = config.endpoints or [config]
    for endpoint in endpoints:
        if endpoint.name == name:
            return endpoint
    return endpoints[0]


def as_dict(config: AppConfig) -> dict[str, Any]:
    return {
        "judge": {
            "name": config.judge.name,
            "base_url": config.judge.base_url,
            "api_key": config.judge.api_key,
            "model": config.judge.model,
            "local_endpoint_mode": config.judge.local_endpoint_mode,
            "bench_lock_url": config.judge.bench_lock_url,
            "bench_unlock_url": config.judge.bench_unlock_url,
            "temperature": config.judge.temperature,
            "max_tokens": config.judge.max_tokens,
            "max_completion_tokens": config.judge.max_completion_tokens,
            "models": config.judge.models or [config.judge.model],
            "endpoints": [
                {
                    "name": endpoint.name,
                    "base_url": endpoint.base_url,
                    "api_key": endpoint.api_key,
                    "model": endpoint.model,
                    "local_endpoint_mode": endpoint.local_endpoint_mode,
                    "bench_lock_url": endpoint.bench_lock_url,
                    "bench_unlock_url": endpoint.bench_unlock_url,
                    "temperature": endpoint.temperature,
                    "max_tokens": endpoint.max_tokens,
                    "max_completion_tokens": endpoint.max_completion_tokens,
                    "models": endpoint.models or [endpoint.model],
                }
                for endpoint in (config.judge.endpoints or [config.judge])
            ],
        }
    }
