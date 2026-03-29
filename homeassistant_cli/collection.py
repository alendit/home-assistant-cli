"""Helpers for domain-oriented collection commands."""
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from homeassistant_cli.config import Configuration
import homeassistant_cli.remote as api


Resolver = Callable[[Dict[str, Any]], Sequence[Optional[str]]]


def get_domain_states(ctx: Configuration, domain: str) -> List[Dict[str, Any]]:
    """Return states for a specific entity domain."""
    prefix = f"{domain}."
    return [
        state
        for state in api.get_states(ctx)
        if state['entity_id'].startswith(prefix)
    ]


def get_item_name(item: Dict[str, Any]) -> str:
    """Return the best available human-friendly name."""
    attributes = item.get('attributes', {})
    return str(
        attributes.get('friendly_name')
        or item.get('name')
        or item.get('original_name')
        or item.get('entity_id')
    )


def filter_items(
    items: Iterable[Dict[str, Any]],
    pattern: str,
) -> List[Dict[str, Any]]:
    """Filter collection items by regex across id and name."""
    regex = re.compile(pattern)
    return [
        item
        for item in items
        if regex.search(item['entity_id']) or regex.search(get_item_name(item))
    ]


def resolve_item(
    items: Iterable[Dict[str, Any]],
    ref: str,
    extra_resolvers: Optional[Sequence[Resolver]] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve an item by exact ref."""
    resolvers = list(extra_resolvers or [])
    matches = []

    for item in items:
        candidates = [item.get('entity_id'), get_item_name(item)]
        for resolver in resolvers:
            candidates.extend(resolver(item))

        exact_matches = [candidate for candidate in candidates if candidate == ref]
        if exact_matches:
            matches.append(item)

    if not matches:
        return None

    if len(matches) > 1:
        raise ValueError(f"Multiple matches found for '{ref}'")

    return matches[0]


def entity_slug(entity_id: str) -> str:
    """Return the part after the entity domain."""
    return entity_id.split(".", 1)[1]
