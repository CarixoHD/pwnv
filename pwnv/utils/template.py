from __future__ import annotations

import re
from typing import Any

from pwnv.models import Challenge

_TEMPLATE_TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")


def _build_template_context(challenge: Challenge) -> dict[str, Any]:
    extras = challenge.extras if isinstance(challenge.extras, dict) else {}
    services = extras.get("services")
    if not isinstance(services, list):
        services = []
    service = services[0] if services else {}
    if not isinstance(service, dict):
        service = {}

    return {
        "challenge": {
            "id": str(challenge.id),
            "name": challenge.name,
            "points": challenge.points,
            "category": challenge.category.name,
            "description": extras.get("description"),
            "slug": extras.get("slug"),
            "tags": challenge.tags or [],
        },
        "services": services,
        "service": service,
        "service_host": service.get("host"),
        "service_port": service.get("port"),
        "service_url": service.get("url"),
        "service_type": service.get("type"),
        "service_raw": service.get("raw"),
        "host": service.get("host"),
        "port": service.get("port"),
        "url": service.get("url"),
    }


def _resolve_template_value(context: dict[str, Any], key: str) -> Any | None:
    value: Any = context
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list):
            if not part.isdigit():
                return None
            idx = int(part)
            if idx >= len(value):
                return None
            value = value[idx]
        else:
            value = getattr(value, part, None)

        if value is None:
            return None

    return value


def render_template(text: str, challenge: Challenge) -> str:
    import json

    context = _build_template_context(challenge)

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = _resolve_template_value(context, key)
        if value is None:
            return match.group(0)
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    return _TEMPLATE_TOKEN_RE.sub(_replace, text)
