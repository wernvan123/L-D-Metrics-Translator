from __future__ import annotations

import json
from datetime import datetime, timezone

from app import db


class BehavioralBias(db.Model):
    """Structured catalog of behavioral biases, heuristics, and related metadata."""

    __tablename__ = "behavioral_biases"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    short_description = db.Column(db.Text)
    detailed_description = db.Column(db.Text)
    countermeasures = db.Column(db.Text)  # JSON array of counter-bias actions
    tags = db.Column(db.Text)             # JSON array of taxonomy tags
    trigger_keywords = db.Column(db.Text) # JSON array of keyword hints
    model_framework = db.Column(db.String(255))
    source_reference = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_date = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<BehavioralBias {self.slug}>"

    # ---- JSON helpers -------------------------------------------------
    @staticmethod
    def _loads_list(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            data = json.loads(value)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _dump_list(value: list[str] | str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, list):
            return json.dumps(value)
        return json.dumps([value])

    # ---- Mutator helpers ---------------------------------------------
    def set_countermeasures(self, items: list[str] | str | None) -> None:
        self.countermeasures = self._dump_list(items)

    def set_tags(self, items: list[str] | str | None) -> None:
        self.tags = self._dump_list(items)

    def set_trigger_keywords(self, items: list[str] | str | None) -> None:
        self.trigger_keywords = self._dump_list(items)

    # ---- Accessors ----------------------------------------------------
    @property
    def countermeasures_list(self) -> list[str]:
        return self._loads_list(self.countermeasures)

    @property
    def tags_list(self) -> list[str]:
        return self._loads_list(self.tags)

    @property
    def trigger_keywords_list(self) -> list[str]:
        return self._loads_list(self.trigger_keywords)

    # ---- Serialization -----------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "short_description": self.short_description,
            "detailed_description": self.detailed_description,
            "countermeasures": self._loads_list(self.countermeasures),
            "tags": self._loads_list(self.tags),
            "trigger_keywords": self._loads_list(self.trigger_keywords),
            "model_framework": self.model_framework,
            "source_reference": self.source_reference,
            "is_active": self.is_active,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "updated_date": self.updated_date.isoformat() if self.updated_date else None,
        }
