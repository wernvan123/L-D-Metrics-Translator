"""
Seed minimal Outcomes, Metric Types, and Metrics, and associate them to existing
Competencies from the seeded Frameworks. This script is idempotent: it checks for
existing rows by name and only inserts missing records.
"""
from datetime import datetime, timezone

from app import create_app, db
from app.models import LDOutcome, MetricType, Metric, Framework, Competency, competency_metrics


def get_or_create_outcome(name: str, description: str = None) -> LDOutcome:
    o = LDOutcome.query.filter_by(name=name).first()
    if o:
        return o
    o = LDOutcome(name=name, description=description or f"Outcome: {name}")
    db.session.add(o)
    db.session.commit()
    return o


def get_or_create_type(name: str, description: str = None, category: str = None) -> MetricType:
    t = MetricType.query.filter_by(name=name).first()
    if t:
        return t
    t = MetricType(name=name, description=description or f"Type: {name}", category=category)
    db.session.add(t)
    db.session.commit()
    return t


def get_or_create_metric(name: str, outcome: LDOutcome, mtype: MetricType, **kwargs) -> Metric:
    m = Metric.query.filter_by(name=name).first()
    if m:
        return m
    m = Metric(
        name=name,
        outcome_id=outcome.id,
        metric_type_id=mtype.id,
        description=kwargs.get('description'),
        example=kwargs.get('example'),
        measurement_method=kwargs.get('measurement_method'),
        data_source=kwargs.get('data_source'),
        frequency=kwargs.get('frequency'),
        unit_of_measure=kwargs.get('unit_of_measure'),
        data_collection=kwargs.get('data_collection'),
        success_criteria=kwargs.get('success_criteria'),
        created_date=datetime.now(timezone.utc),
    )
    db.session.add(m)
    db.session.commit()
    return m


def ensure_assoc(comp: Competency, metric: Metric):
    # Many-to-many via competency_metrics table
    link = db.session.execute(
        competency_metrics.select()
        .where(competency_metrics.c.competency_id == comp.id)
        .where(competency_metrics.c.metric_id == metric.id)
    ).first()
    if link:
        return
    db.session.execute(
        competency_metrics.insert().values(competency_id=comp.id, metric_id=metric.id)
    )
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        # Outcomes
        engagement = get_or_create_outcome("Engagement", "Employee engagement and participation in learning")
        productivity = get_or_create_outcome("Productivity", "Output and efficiency improvements")
        retention = get_or_create_outcome("Retention", "Retention of knowledge and talent")

        # Types (keep category None for compatibility with is_valid_category)
        behavioral = get_or_create_type("Behavioral", "Behavior change/observations", category=None)
        operational = get_or_create_type("Operational", "Operational metrics (time, cost)", category=None)
        neuroscience = get_or_create_type("Neuroscience", "Neuroscience-informed indicators", category=None)

        # Metrics (6+ examples)
        m1 = get_or_create_metric(
            "Training Completion Rate",
            engagement,
            operational,
            description="Percentage of learners who completed assigned training within the period",
            example="85% completion within 30 days",
            measurement_method="Analytics",
            data_source="LMS",
            frequency="Monthly",
            unit_of_measure="Percent",
            data_collection="Monthly",
            success_criteria=">= 80%",
        )
        m2 = get_or_create_metric(
            "Session Participation",
            engagement,
            behavioral,
            description="Average number of sessions attended per learner",
            example="2.1 sessions/learner per month",
            measurement_method="Analytics",
            data_source="LMS/Virtual Classroom",
            frequency="Monthly",
            unit_of_measure="Sessions per learner",
            data_collection="Monthly",
            success_criteria=">= 2",
        )
        m3 = get_or_create_metric(
            "Knowledge Retention Score",
            retention,
            behavioral,
            description="Average post-training retention assessment score",
            example="Average 78% at 30-day follow-up",
            measurement_method="Survey",
            data_source="Assessment platform",
            frequency="Monthly",
            unit_of_measure="Percent",
            data_collection="Monthly",
            success_criteria=">= 75%",
        )
        m4 = get_or_create_metric(
            "Time to Productivity",
            productivity,
            operational,
            description="Average time for new hires to reach expected productivity",
            example="On average 60 days to productivity",
            measurement_method="Analytics",
            data_source="HRIS/Performance systems",
            frequency="Quarterly",
            unit_of_measure="Days",
            data_collection="Monthly",
            success_criteria="<= 60 days",
        )
        m5 = get_or_create_metric(
            "Behavioral Application Index",
            productivity,
            behavioral,
            description="Self/manager-reported frequency of applying learned behaviors on the job",
            example="3.8/5 behavior application",
            measurement_method="Survey",
            data_source="Pulse surveys",
            frequency="Monthly",
            unit_of_measure="Scale (1-5)",
            data_collection="Monthly",
            success_criteria=">= 4.0",
        )
        m6 = get_or_create_metric(
            "Cognitive Load Indicator",
            retention,
            neuroscience,
            description="Subjective cognitive load during learning tasks",
            example="Average 2.6/5 cognitive load",
            measurement_method="Survey",
            data_source="Experience surveys",
            frequency="Monthly",
            unit_of_measure="Scale (1-5)",
            data_collection="Monthly",
            success_criteria="<= 3.0",
        )

        # Associate metrics with some competencies from any existing frameworks
        frameworks = Framework.query.order_by(Framework.sort_order, Framework.name).all()
        comps = []
        for fw in frameworks:
            comps.extend(fw.competencies)
        # Take up to first 6 competencies to map 1:1
        pairs = list(zip(comps[:6], [m1, m2, m3, m4, m5, m6])) if comps else []
        for comp, metric in pairs:
            ensure_assoc(comp, metric)

        print("Seed completed:")
        print(f"Outcomes: {LDOutcome.query.count()} | Types: {MetricType.query.count()} | Metrics: {Metric.query.count()}")


if __name__ == "__main__":
    main()
