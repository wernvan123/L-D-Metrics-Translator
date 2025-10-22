"""Service functions to query tiered knowledge base resources for event analysis."""

from __future__ import annotations

from typing import Iterable, List, Optional
from collections import defaultdict

from sqlalchemy.orm import Query
from sqlalchemy import or_, func

from app import db
from app.models import KnowledgeCategory, KnowledgeResource


def _base_resource_query() -> Query:
    return KnowledgeResource.query.order_by(KnowledgeResource.tier.asc(), KnowledgeResource.id.asc())


def get_resources_by_tier(tier: str, limit: Optional[int] = None) -> List[KnowledgeResource]:
    query = _base_resource_query().filter(KnowledgeResource.tier == tier.lower())
    if limit:
        query = query.limit(limit)
    return query.all()


def get_resources_for_context(context: Optional[str], max_results: int = 20) -> List[KnowledgeResource]:
    query = _base_resource_query()
    if context:
        query = query.filter(KnowledgeResource.context == str(context))
    return query.limit(max_results).all()


def get_bias_resources(limit: int = 10) -> List[KnowledgeResource]:
    bias_category = KnowledgeCategory.query.filter(
        KnowledgeCategory.name.ilike('%Biases%')
    ).first()
    if not bias_category:
        return []
    return (
        _base_resource_query()
        .filter(KnowledgeResource.category_id == bias_category.id)
        .limit(limit)
        .all()
    )


def get_random_bias_resources(limit: int = 5) -> List[KnowledgeResource]:
    bias_category = KnowledgeCategory.query.filter(
        KnowledgeCategory.name.ilike('%Biases%')
    ).first()
    if not bias_category:
        return []
    return (
        KnowledgeResource.query
        .filter(KnowledgeResource.category_id == bias_category.id)
        .order_by(func.random())
        .limit(limit)
        .all()
    )


def serialize_resource(resource: KnowledgeResource) -> dict:
    return {
        'id': resource.id,
        'heading': resource.heading,
        'content': resource.content,
        'tier': resource.tier,
        'tags': resource.tags.split(',') if resource.tags else [],
        'context': resource.context,
        'category': resource.category.name if resource.category else None,
    }


def serialize_resources(resources: Iterable[KnowledgeResource]) -> List[dict]:
    return [serialize_resource(r) for r in resources]


def search_bias_resources(text: Optional[str], limit: int = 5) -> List[KnowledgeResource]:
    if not text:
        return []

    terms = [term.strip() for term in text.lower().split() if len(term.strip()) > 2]
    if not terms:
        return []

    query = (
        KnowledgeResource.query
        .join(KnowledgeCategory, KnowledgeResource.category_id == KnowledgeCategory.id, isouter=True)
        .filter(KnowledgeCategory.name.ilike('%Bias%'))
    )

    conditions = []
    for term in terms:
        like_pattern = f'%{term}%'
        conditions.append(
            or_(
                KnowledgeResource.heading.ilike(like_pattern),
                KnowledgeResource.content.ilike(like_pattern),
                KnowledgeResource.tags.ilike(like_pattern),
                KnowledgeResource.context.ilike(like_pattern),
                KnowledgeResource.reference.ilike(like_pattern),
            )
        )

    if conditions:
        query = query.filter(or_(*conditions))

    tier_bonus = {'t1': 3, 't2': 2, 't3': 1}
    max_candidates = max(limit * 5, limit + 5)
    candidates = query.limit(max_candidates).all()

    scored: List[tuple[int, KnowledgeResource]] = []
    for resource in candidates:
        text_blob = " ".join(filter(None, [
            resource.heading,
            resource.content,
            resource.tags,
            resource.context,
            resource.reference,
        ])).lower()

        matched_terms = {term for term in terms if term in text_blob}
        if not matched_terms:
            continue

        score = len(matched_terms) * 10
        score += tier_bonus.get(resource.tier.lower() if resource.tier else '', 0)
        scored.append((score, resource))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [resource for _, resource in scored[:limit]]
