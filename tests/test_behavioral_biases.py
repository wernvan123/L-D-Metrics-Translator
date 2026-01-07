import pytest

from app import db
from app.models_behavioral_bias import BehavioralBias
from app.services import behavioral_biases
from app.ollama_integration import event_analyzer


@pytest.fixture()
def create_bias(app):
    """Factory to create and persist BehavioralBias records for tests."""
    def _create(
        name="Authority Bias",
        slug="authority-bias",
        short_description="Overweighting opinions from authority figures.",
        trigger_keywords=None,
        countermeasures=None,
        tags=None,
    ):
        with app.app_context():
            bias = BehavioralBias(
                name=name,
                slug=slug,
                short_description=short_description,
                detailed_description="Detailed context",
                model_framework="Prospect Theory",
                source_reference="Test Source",
                is_active=True,
            )
            bias.set_trigger_keywords(trigger_keywords or ["authority"])
            bias.set_countermeasures(countermeasures or ["Invite dissenting views"])
            bias.set_tags(tags or ["decision-making"])
            db.session.add(bias)
            db.session.commit()
            return {"id": bias.id, "name": bias.name}

    return _create


def test_behavioral_bias_service_matches_keywords(app, create_bias):
    bias_info = create_bias()

    with app.app_context():
        results = behavioral_biases.search_biases(keywords=["authority"], limit=5)
        assert len(results) == 1
        assert results[0].name == bias_info["name"]


def test_get_bias_knowledge_endpoint_returns_biases(app, client, create_bias):
    app.config["ENABLE_EVENT_KB"] = True
    bias_info = create_bias()

    response = client.get("/api/knowledge/biases?q=authority")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert any(item["name"] == bias_info["name"] for item in data["items"])
    sample = next(item for item in data["items"] if item["name"] == bias_info["name"])
    assert "countermeasures" in sample and sample["countermeasures"]
    assert "trigger_keywords" in sample and sample["trigger_keywords"]


def test_analyze_event_includes_behavioral_biases(app, client, create_bias, monkeypatch):
    app.config["ENABLE_EVENT_KB"] = True
    bias_info = create_bias()

    def fake_analyze_event(event_description, selected_metrics=None):
        return {
            "learning_needs": [],
            "recommended_metrics": [],
            "interventions": [],
            "success_measures": [],
            "biases": [],
        }

    monkeypatch.setattr(event_analyzer, "analyze_event", fake_analyze_event)
    monkeypatch.setattr(event_analyzer.ollama, "available", False)

    payload = {"event_description": "Our executive said we must do it this way."}
    response = client.post("/api/analyze-event", json=payload)
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert "kb" in data and "biases" in data["kb"]
    assert any(item["name"] == bias_info["name"] for item in data["kb"]["biases"])
