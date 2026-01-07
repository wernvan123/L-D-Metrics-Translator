"""Query helpers for BehavioralBias records."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Query

from app import db
from app.models_behavioral_bias import BehavioralBias


def _base_query() -> Query:
    return (
        BehavioralBias.query
        .filter(BehavioralBias.is_active.is_(True))
        .order_by(func.lower(BehavioralBias.name))
    )


def _normalize_terms(values: Optional[Sequence[str]]) -> List[str]:
    if not values:
        return []
    terms: List[str] = []
    seen = set()
    for value in values:
        if not value:
            continue
        for term in str(value).replace(';', '\n').splitlines():
            candidate = term.strip().lower()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            terms.append(candidate)
    return terms


def search_biases(
    text: Optional[str] = None,
    *,
    keywords: Optional[Sequence[str]] = None,
    tags: Optional[Sequence[str]] = None,
    limit: int = 10,
) -> List[BehavioralBias]:
    """Search behavioral biases by free text, keywords, or tags."""
    query = _base_query()

    filters = []
    normalized_keywords = _normalize_terms(keywords)
    normalized_tags = _normalize_terms(tags)

    if text:
        text = text.strip()
        if text:
            pattern = f"%{text.lower()}%"
            filters.append(
                or_(
                    func.lower(BehavioralBias.name).ilike(pattern),
                    func.lower(BehavioralBias.short_description).ilike(pattern),
                    func.lower(BehavioralBias.detailed_description).ilike(pattern),
                    func.lower(BehavioralBias.model_framework).ilike(pattern),
                    func.lower(BehavioralBias.source_reference).ilike(pattern),
                    func.lower(BehavioralBias.tags).ilike(pattern),
                    func.lower(BehavioralBias.countermeasures).ilike(pattern),
                    func.lower(BehavioralBias.trigger_keywords).ilike(pattern),
                )
            )

    if normalized_keywords:
        for keyword in normalized_keywords:
            like_pattern = f"%\"{keyword}\"%"
            filters.append(func.lower(BehavioralBias.trigger_keywords).like(like_pattern))

    if normalized_tags:
        for tag in normalized_tags:
            filters.append(func.lower(BehavioralBias.tags).like(f"%{tag}%"))

    if filters:
        query = query.filter(or_(*filters))

    limit = max(1, min(limit, 50))
    return query.limit(limit).all()


def serialize_bias(bias: BehavioralBias) -> dict:
    return {
        "id": bias.id,
        "name": bias.name,
        "slug": bias.slug,
        "short_description": bias.short_description,
        "detailed_description": bias.detailed_description,
        "countermeasures": bias.countermeasures_list,
        "tags": bias.tags_list,
        "trigger_keywords": bias.trigger_keywords_list,
        "model_framework": bias.model_framework,
        "source_reference": bias.source_reference,
    }


def serialize_biases(biases: Iterable[BehavioralBias]) -> List[dict]:
    return [serialize_bias(b) for b in biases]


def get_random_biases(limit: int = 5) -> List[BehavioralBias]:
    limit = max(1, min(limit, 50))
    return (
        BehavioralBias.query
        .filter(BehavioralBias.is_active.is_(True))
        .order_by(func.random())
        .limit(limit)
        .all()
    )
