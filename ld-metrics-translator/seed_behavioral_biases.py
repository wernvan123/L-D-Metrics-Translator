"""Seed script for behavioral biases catalog."""

from app import create_app, db
from app.models_behavioral_bias import BehavioralBias

SEED_BIASES = [
    {
        "name": "Status Quo Bias",
        "slug": "status-quo-bias",
        "short_description": "Preference for existing practices even when evidence suggests change would help.",
        "detailed_description": "Teams default to familiar routines and resist experimentation despite performance gaps.",
        "countermeasures": [
            "Surface switching costs explicitly",
            "Pilot safe-to-try experiments",
            "Set success criteria for limited trials"
        ],
        "tags": ["decision-making", "change", "resistance"],
        "trigger_keywords": [
            "status quo",
            "as usual",
            "keep doing",
            "resistance to change",
            "never tries"
        ],
        "model_framework": "Prospect Theory",
        "source_reference": "Kahneman & Tversky"
    },
    {
        "name": "Authority Bias",
        "slug": "authority-bias",
        "short_description": "Overweighting opinions from senior voices regardless of evidence.",
        "detailed_description": "Teams adopt recommendations from leaders or experts without pressure testing alternatives.",
        "countermeasures": [
            "Invite dissenting views first",
            "Use blind voting before discussion",
            "Ask for evidence instead of rank"
        ],
        "tags": ["leadership", "decision-making"],
        "trigger_keywords": [
            "executive said",
            "boss insisted",
            "leadership presence",
            "obvious choice",
            "instinctively selects"
        ],
        "model_framework": "Influence Heuristics",
        "source_reference": "Cialdini"
    },
    {
        "name": "Halo Effect",
        "slug": "halo-effect",
        "short_description": "One positive trait unduly sways overall judgments.",
        "detailed_description": "Charisma or communication skill leads to blanket approval of a person’s ideas without scrutiny.",
        "countermeasures": [
            "List explicit evaluation criteria",
            "Have independent reviewers score",
            "Separate style cues from evidence"
        ],
        "tags": ["talent", "evaluation"],
        "trigger_keywords": [
            "natural leader",
            "communicates well",
            "executive presence",
            "obvious pick"
        ],
        "model_framework": "Attribution Theory",
        "source_reference": "Thorndike"
    },
]


def seed_behavioral_biases():
    app = create_app()
    with app.app_context():
        created = 0
        for entry in SEED_BIASES:
            existing = BehavioralBias.query.filter_by(slug=entry["slug"]).first()
            if existing:
                continue
            bias = BehavioralBias(
                name=entry["name"],
                slug=entry["slug"],
                short_description=entry.get("short_description"),
                detailed_description=entry.get("detailed_description"),
                model_framework=entry.get("model_framework"),
                source_reference=entry.get("source_reference"),
            )
            bias.set_countermeasures(entry.get("countermeasures"))
            bias.set_tags(entry.get("tags"))
            bias.set_trigger_keywords(entry.get("trigger_keywords"))
            db.session.add(bias)
            created += 1
        if created:
            db.session.commit()
        print(f"Seeded {created} behavioral biases")


if __name__ == "__main__":
    seed_behavioral_biases()
