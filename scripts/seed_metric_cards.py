import os
import sys
import json

# Ensure inner package import
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PKG = os.path.join(ROOT, 'ld-metrics-translator')
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from app import create_app, db  # type: ignore
from app.models import LDOutcome, MetricType, Metric, Framework, Competency  # type: ignore


def get_or_create(model, defaults=None, **kwargs):
    inst = model.query.filter_by(**kwargs).first()
    if inst:
        return inst, False
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    inst = model(**params)
    db.session.add(inst)
    db.session.commit()
    return inst, True


def seed():
    app = create_app('default')
    with app.app_context():
        # Outcomes (exact set)
        dev_res, _ = get_or_create(LDOutcome, name='Development & Resilience', defaults={'description': 'Growth and resilience development.'})
        engagement, _ = get_or_create(LDOutcome, name='Engagement', defaults={'description': 'Employee engagement and energy.'})
        productivity, _ = get_or_create(LDOutcome, name='Productivity', defaults={'description': 'Operational effectiveness.'})
        retention, _ = get_or_create(LDOutcome, name='Retention', defaults={'description': 'Keep top talent.'})

        # Types (exact set)
        foundational, _ = get_or_create(MetricType, name='Foundational', defaults={'description': 'Foundational concept'})
        behavioral, _ = get_or_create(MetricType, name='Behavioral', defaults={'description': 'Behavioral metric'})
        operational, _ = get_or_create(MetricType, name='Operational', defaults={'description': 'Operational KPI'})
        strategic, _ = get_or_create(MetricType, name='Strategic', defaults={'description': 'Strategic outcome'})

        # Framework + Competency
        fw, _ = get_or_create(Framework, slug='five-practices', defaults={
            'name': 'The Five Practices of Exemplary Leadership',
            'description': 'Kouzes & Posner',
            'source': 'Kouzes & Posner',
            'is_builtin': True,
            'is_active': True,
        })
        comp_ctp, _ = get_or_create(Competency, framework_id=fw.id, slug='challenge-the-process', defaults={
            'name': 'Challenge the Process',
            'description': 'Search for opportunities by seizing the initiative and by looking outward for innovative ways to improve.'
        })

        # 1) CONCEPT: Growth Mindset
        gm_chain = {
            "drives_behaviors": ["Embracing challenges", "Persisting through setbacks", "Seeking constructive feedback"],
            "measured_by_kpis": ["Skill Application Rate", "Voluntary Learning Hours"],
            "leads_to_outcomes": ["Increased Resilience", "Faster Skill Development"]
        }
        growth_mindset, created_gm = get_or_create(
            Metric,
            name='Growth Mindset',
            defaults={
                'description': 'Improve early learner experience. Growth Mindset belief that abilities can improve with effort.',
                'identifier_type': 'concept',
                'driver_chain': json.dumps(gm_chain, ensure_ascii=False),
                'data_collection': 'Survey/Assessment',
                'frequency': 'Annually',
                'outcome_id': dev_res.id,
                'metric_type_id': foundational.id,
            }
        )
        if not created_gm:
            growth_mindset.description = 'Improve early learner experience. Growth Mindset belief that abilities can improve with effort.'
            growth_mindset.identifier_type = 'concept'
            growth_mindset.driver_chain = json.dumps(gm_chain, ensure_ascii=False)
            growth_mindset.data_collection = 'Survey/Assessment'
            growth_mindset.frequency = 'Annually'
            growth_mindset.outcome_id = dev_res.id
            growth_mindset.metric_type_id = foundational.id
            db.session.commit()

        # 2) BEHAVIOR: Giving Recognition
        gr_chain = {
            "driven_by_concepts": ["Empathy", "Social Awareness"],
            "measured_by_kpis": ["Recognition Frequency", "Employee Net Promoter Score (eNPS)"],
            "leads_to_outcomes": ["Increased Employee Engagement", "Improved Team Morale"]
        }
        giving_recognition, created_gr = get_or_create(
            Metric,
            name='Giving Recognition',
            defaults={
                'description': 'Actively acknowledging others’ contributions and effort.',
                'identifier_type': 'behavior',
                'driver_chain': json.dumps(gr_chain, ensure_ascii=False),
                'data_collection': '360/Manager Feedback',
                'frequency': 'Quarterly',
                'outcome_id': engagement.id,
                'metric_type_id': behavioral.id,
            }
        )
        if not created_gr:
            giving_recognition.description = 'Actively acknowledging others’ contributions and effort.'
            giving_recognition.identifier_type = 'behavior'
            giving_recognition.driver_chain = json.dumps(gr_chain, ensure_ascii=False)
            giving_recognition.data_collection = '360/Manager Feedback'
            giving_recognition.frequency = 'Quarterly'
            giving_recognition.outcome_id = engagement.id
            giving_recognition.metric_type_id = behavioral.id
            db.session.commit()

        # 3) KPI: Time to Productivity
        ttp_chain = {
            "measures_behaviors": ["Effective Onboarding", "Manager Coaching"],
            "indicates_concepts": ["Learning Agility", "Clarity of Role"],
            "leads_to_outcomes": ["Faster ROI on New Hires", "Increased Operational Efficiency"]
        }
        time_to_productivity, created_ttp = get_or_create(
            Metric,
            name='Time to Productivity',
            defaults={
                'description': 'Time from start date to target performance.',
                'identifier_type': 'kpi',
                'driver_chain': json.dumps(ttp_chain, ensure_ascii=False),
                'data_collection': 'HRIS/Business Data',
                'frequency': 'Per New Hire Cohort',
                'outcome_id': productivity.id,
                'metric_type_id': operational.id,
            }
        )
        if not created_ttp:
            time_to_productivity.description = 'Time from start date to target performance.'
            time_to_productivity.identifier_type = 'kpi'
            time_to_productivity.driver_chain = json.dumps(ttp_chain, ensure_ascii=False)
            time_to_productivity.data_collection = 'HRIS/Business Data'
            time_to_productivity.frequency = 'Per New Hire Cohort'
            time_to_productivity.outcome_id = productivity.id
            time_to_productivity.metric_type_id = operational.id
            db.session.commit()

        # 4) OUTCOME: Improved Employee Retention
        ier_chain = {
            "driven_by_behaviors": ["Conducting regular 1-on-1s", "Providing development opportunities", "Giving recognition"],
            "driven_by_concepts": ["Psychological Safety", "Intrinsic Motivation"],
            "measured_by_kpis": ["Employee Turnover Rate", "Regretted Attrition %"]
        }
        improved_retention, created_ier = get_or_create(
            Metric,
            name='Improved Employee Retention',
            defaults={
                'description': 'Sustained reduction in regretted attrition.',
                'identifier_type': 'outcome',
                'driver_chain': json.dumps(ier_chain, ensure_ascii=False),
                'data_collection': 'HRIS Data',
                'frequency': 'Quarterly',
                'outcome_id': retention.id,
                'metric_type_id': strategic.id,
            }
        )
        if not created_ier:
            improved_retention.description = 'Sustained reduction in regretted attrition.'
            improved_retention.identifier_type = 'outcome'
            improved_retention.driver_chain = json.dumps(ier_chain, ensure_ascii=False)
            improved_retention.data_collection = 'HRIS Data'
            improved_retention.frequency = 'Quarterly'
            improved_retention.outcome_id = retention.id
            improved_retention.metric_type_id = strategic.id
            db.session.commit()

        # Link Growth Mindset to Challenge the Process competency
        comp_ctp.metrics = list(set(comp_ctp.metrics + [growth_mindset]))
        db.session.commit()

        print('Seeded driver cards:')
        print(' - Growth Mindset (CONCEPT) id=', growth_mindset.id)
        print(' - Giving Recognition (BEHAVIOR) id=', giving_recognition.id)
        print(' - Time to Productivity (KPI) id=', time_to_productivity.id)
        print(' - Improved Employee Retention (OUTCOME) id=', improved_retention.id)


if __name__ == '__main__':
    app = create_app('default')
    with app.app_context():
        seed()
