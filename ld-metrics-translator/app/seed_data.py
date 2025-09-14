"""
Comprehensive data seeding script for L&D Metrics Translator.

This script populates the database with:
- All 5 L&D Outcomes (Engagement, Retention, Behavior Change, Performance, Well-being)
- All 3 Metric Types (Operational KPI, Behavioral Metric, Neuroscience-Based Metric)
- 20+ sample metrics covering all combinations with realistic descriptions and examples
"""

from app import db
from app.models import LDOutcome, MetricType, Metric
from datetime import datetime
import sys


class DataSeeder:
    """Handles comprehensive data seeding for the L&D Metrics Translator."""
    
    def __init__(self):
        self.outcomes_data = []
        self.metric_types_data = []
        self.metrics_data = []
        self._prepare_seed_data()
    
    def _prepare_seed_data(self):
        """Prepare all seed data structures."""
        self._prepare_outcomes()
        self._prepare_metric_types()
        self._prepare_metrics()
    
    def _prepare_outcomes(self):
        """Prepare L&D Outcomes data."""
        self.outcomes_data = [
            {
                'name': 'Employee Engagement',
                'description': 'Measures how actively involved and committed employees are to their learning and work. Includes participation rates, enthusiasm levels, and voluntary engagement in development activities.'
            },
            {
                'name': 'Employee Retention',
                'description': 'Tracks employee retention rates and factors that contribute to keeping talent. Focuses on reducing turnover and improving employee loyalty through effective L&D programs.'
            },
            {
                'name': 'Behavior Change',
                'description': 'Evaluates the extent to which learning translates into observable behavior modifications. Measures actual application of learned skills and knowledge in the workplace.'
            },
            {
                'name': 'Performance',
                'description': 'Assesses improvements in job performance and productivity following learning interventions. Includes both individual and team performance metrics.'
            },
            {
                'name': 'Well-Being',
                'description': 'Measures employee satisfaction, stress levels, and overall workplace wellness. Encompasses mental health, work-life balance, and job satisfaction indicators.'
            }
        ]
    
    def _prepare_metric_types(self):
        """Prepare Metric Types data."""
        self.metric_types_data = [
            {
                'name': 'Operational KPI',  # Will be stored as 'Operational KPI' due to title() validation
                'description': 'Quantifiable business metrics that directly impact organizational operations and outcomes. These are measurable indicators tied to business performance and ROI.'
            },
            {
                'name': 'Behavioral Metric',
                'description': 'Observable and measurable behaviors that indicate learning effectiveness and application. Focus on actions, participation, and behavioral changes in the workplace.'
            },
            {
                'name': 'Neuroscience-Based Metric',
                'description': 'Brain-based metrics and concepts that explain the underlying cognitive and neurological processes of learning, memory, and behavior change.'
            }
        ]
    
    def _prepare_metrics(self):
        """Prepare comprehensive metrics data covering all outcome-type combinations."""
        self.metrics_data = [
            # ENGAGEMENT + OPERATIONAL KPI
            {
                'name': 'Employee Net Promoter Score (eNPS)',
                'description': 'Measures employee loyalty and likelihood to recommend the organization as a place to work. Calculated by subtracting detractors from promoters.',
                'example': 'Survey question: "On a scale of 0-10, how likely are you to recommend this company as a place to work?" Score = % Promoters (9-10) - % Detractors (0-6)',
                'outcome': 'Employee Engagement',
                'type': 'Operational KPI'
            },
            {
                'name': 'Learning Program Completion Rate',
                'description': 'Percentage of employees who complete assigned learning programs within the specified timeframe.',
                'example': 'If 850 out of 1000 employees complete their mandatory training by the deadline, the completion rate is 85%',
                'outcome': 'Employee Engagement',
                'type': 'Operational KPI'
            },
            {
                'name': 'Training ROI',
                'description': 'Return on investment for training programs, calculated as the financial benefit minus training costs divided by training costs.',
                'example': 'ROI = (Training Benefits - Training Costs) / Training Costs × 100. A $100k training program that generates $150k in benefits has 50% ROI',
                'outcome': 'Employee Engagement',
                'type': 'Operational KPI'
            },
            
            # ENGAGEMENT + BEHAVIORAL METRIC
            {
                'name': 'Active Participation in Workshops',
                'description': 'Frequency and quality of employee participation in learning workshops, measured through attendance, questions asked, and contributions made.',
                'example': 'Track attendance rates, number of questions/comments per session, and peer feedback on participation quality during workshops',
                'outcome': 'Employee Engagement',
                'type': 'Behavioral Metric'
            },
            {
                'name': 'Voluntary Learning Hours',
                'description': 'Number of hours employees spend on optional learning activities beyond mandatory training requirements.',
                'example': 'Employee spends 10 hours per month on optional online courses, webinars, or self-directed learning activities',
                'outcome': 'Employee Engagement',
                'type': 'Behavioral Metric'
            },
            
            # ENGAGEMENT + NEUROSCIENCE-BASED METRIC
            {
                'name': 'Attention',
                'description': 'The cognitive process of selectively concentrating on learning content while filtering out distractions. Critical for effective information processing.',
                'example': 'Measured through eye-tracking during e-learning, focus duration metrics, or attention-based assessments during training sessions',
                'outcome': 'Employee Engagement',
                'type': 'Neuroscience-Based Metric'
            },
            {
                'name': 'Intrinsic Motivation',
                'description': 'Internal drive to learn and grow without external rewards. Linked to dopamine pathways and self-determination theory.',
                'example': 'Assessed through surveys measuring autonomy, mastery, and purpose; or neuroimaging showing activation in reward centers during learning',
                'outcome': 'Employee Engagement',
                'type': 'Neuroscience-Based Metric'
            },
            
            # RETENTION + OPERATIONAL KPI
            {
                'name': 'Employee Turnover Rate',
                'description': 'Percentage of employees who leave the organization within a specific period, often measured annually.',
                'example': 'If 50 employees leave out of 500 total employees in a year, the turnover rate is 10%',
                'outcome': 'Employee Retention',
                'type': 'Operational KPI'
            },
            {
                'name': 'Cost per Hire',
                'description': 'Total cost associated with recruiting and hiring a new employee, including advertising, interviewing, and onboarding expenses.',
                'example': 'Total recruitment costs of $15,000 divided by 10 new hires equals $1,500 cost per hire',
                'outcome': 'Employee Retention',
                'type': 'Operational KPI'
            },
            
            # RETENTION + BEHAVIORAL METRIC
            {
                'name': 'Internal Mobility Rate',
                'description': 'Percentage of positions filled by internal candidates through promotions or lateral moves, indicating career development effectiveness.',
                'example': 'If 30 out of 50 open positions are filled internally, the internal mobility rate is 60%',
                'outcome': 'Employee Retention',
                'type': 'Behavioral Metric'
            },
            {
                'name': 'Mentorship Participation',
                'description': 'Level of employee engagement in formal and informal mentoring relationships, both as mentors and mentees.',
                'example': 'Track number of active mentor-mentee pairs, frequency of meetings, and duration of mentoring relationships',
                'outcome': 'Employee Retention',
                'type': 'Behavioral Metric'
            },
            
            # RETENTION + NEUROSCIENCE-BASED METRIC
            {
                'name': 'Psychological Safety',
                'description': 'Neurological state where the brain perceives the environment as safe for risk-taking, learning, and authentic self-expression.',
                'example': 'Measured through stress hormone levels, brain imaging showing reduced amygdala activation, or behavioral indicators of openness',
                'outcome': 'Employee Retention',
                'type': 'Neuroscience-Based Metric'
            },
            
            # BEHAVIOR CHANGE + OPERATIONAL KPI
            {
                'name': 'Skill Application Rate',
                'description': 'Percentage of learned skills that are actively applied in the workplace within a specified timeframe after training.',
                'example': 'If employees apply 7 out of 10 skills learned in leadership training within 3 months, the application rate is 70%',
                'outcome': 'Behavior Change',
                'type': 'Operational KPI'
            },
            {
                'name': '360-Degree Feedback Improvement',
                'description': 'Measurable improvement in leadership or behavioral competencies as rated by supervisors, peers, and direct reports.',
                'example': 'Communication skills rating improves from 3.2 to 4.1 on a 5-point scale based on 360-degree feedback surveys',
                'outcome': 'Behavior Change',
                'type': 'Operational KPI'
            },
            
            # BEHAVIOR CHANGE + BEHAVIORAL METRIC
            {
                'name': 'Habit Formation Tracking',
                'description': 'Monitoring the development and consistency of new workplace behaviors or habits following learning interventions.',
                'example': 'Track daily practice of new time management techniques for 66 days (average habit formation period) with consistency metrics',
                'outcome': 'Behavior Change',
                'type': 'Behavioral Metric'
            },
            
            # BEHAVIOR CHANGE + NEUROSCIENCE-BASED METRIC
            {
                'name': 'Neuroplasticity',
                'description': 'The brain\'s ability to reorganize and form new neural connections throughout life, enabling learning and behavior change.',
                'example': 'Measured through neuroimaging showing structural brain changes, or cognitive assessments demonstrating improved neural efficiency',
                'outcome': 'Behavior Change',
                'type': 'Neuroscience-Based Metric'
            },
            {
                'name': 'Memory Consolidation',
                'description': 'Process by which temporary memories are transformed into stable, long-term memories through protein synthesis and neural pathway strengthening.',
                'example': 'Assessed through spaced repetition effectiveness, sleep impact on learning retention, or memory recall tests over time',
                'outcome': 'Behavior Change',
                'type': 'Neuroscience-Based Metric'
            },
            
            # PERFORMANCE + OPERATIONAL KPI
            {
                'name': 'Productivity Index',
                'description': 'Quantitative measure of output per unit of input, typically measuring work completed relative to time or resources invested.',
                'example': 'Sales team increases from 50 to 65 deals closed per month after sales training, representing a 30% productivity increase',
                'outcome': 'Performance',
                'type': 'Operational KPI'
            },
            {
                'name': 'Quality Score',
                'description': 'Measurement of work quality standards, error rates, or customer satisfaction related to employee performance.',
                'example': 'Customer service quality scores improve from 4.2 to 4.7 out of 5.0 after communication skills training',
                'outcome': 'Performance',
                'type': 'Operational KPI'
            },
            
            # PERFORMANCE + BEHAVIORAL METRIC
            {
                'name': 'Goal Achievement Rate',
                'description': 'Percentage of individual or team goals met within specified timeframes, indicating performance effectiveness.',
                'example': 'Employee achieves 8 out of 10 quarterly objectives, resulting in an 80% goal achievement rate',
                'outcome': 'Performance',
                'type': 'Behavioral Metric'
            },
            
            # PERFORMANCE + NEUROSCIENCE-BASED METRIC
            {
                'name': 'Cognitive Load',
                'description': 'Amount of mental effort being used in working memory during task performance. Optimal load enhances learning and performance.',
                'example': 'Measured through dual-task paradigms, pupil dilation, or EEG during complex problem-solving activities',
                'outcome': 'Performance',
                'type': 'Neuroscience-Based Metric'
            },
            
            # WELL-BEING + OPERATIONAL KPI
            {
                'name': 'Employee Satisfaction Score',
                'description': 'Quantitative measure of employee contentment with their job, work environment, and organizational culture.',
                'example': 'Annual employee satisfaction survey shows average score of 4.3 out of 5.0 across all departments',
                'outcome': 'Well-Being',
                'type': 'Operational KPI'
            },
            {
                'name': 'Absenteeism Rate',
                'description': 'Percentage of scheduled work time that employees are absent, often indicating stress, burnout, or disengagement.',
                'example': 'Department has 3% absenteeism rate compared to industry average of 5%, indicating better well-being',
                'outcome': 'Well-Being',
                'type': 'Operational KPI'
            },
            
            # WELL-BEING + BEHAVIORAL METRIC
            {
                'name': 'Work-Life Balance Indicators',
                'description': 'Observable behaviors indicating healthy boundaries between work and personal life, such as after-hours email patterns.',
                'example': 'Track email response times after hours, vacation day usage, and participation in wellness programs',
                'outcome': 'Well-Being',
                'type': 'Behavioral Metric'
            },
            
            # WELL-BEING + NEUROSCIENCE-BASED METRIC
            {
                'name': 'Stress Response',
                'description': 'Physiological and neurological reactions to workplace stressors, involving cortisol release and sympathetic nervous system activation.',
                'example': 'Measured through cortisol levels, heart rate variability, or brain imaging showing amygdala activation patterns',
                'outcome': 'Well-Being',
                'type': 'Neuroscience-Based Metric'
            }
        ]
    
    def validate_data_integrity(self):
        """Validate that all data combinations are covered and data is consistent."""
        print("Validating data integrity...")
        
        # Check that we have all expected outcomes
        outcome_names = {item['name'] for item in self.outcomes_data}
        expected_outcomes = {'Employee Engagement', 'Employee Retention', 'Behavior Change', 'Performance', 'Well-Being'}
        if outcome_names != expected_outcomes:
            raise ValueError(f"Missing outcomes: {expected_outcomes - outcome_names}")
        
        # Check that we have all expected metric types
        type_names = {item['name'] for item in self.metric_types_data}
        expected_types = {'Operational KPI', 'Behavioral Metric', 'Neuroscience-Based Metric'}
        if type_names != expected_types:
            raise ValueError(f"Missing metric types: {expected_types - type_names}")
        
        # Check that all metrics reference valid outcomes and types
        for metric in self.metrics_data:
            if metric['outcome'] not in outcome_names:
                raise ValueError(f"Invalid outcome '{metric['outcome']}' in metric '{metric['name']}'")
            if metric['type'] not in type_names:
                raise ValueError(f"Invalid type '{metric['type']}' in metric '{metric['name']}'")
        
        # Check for coverage of all combinations
        combinations = {(metric['outcome'], metric['type']) for metric in self.metrics_data}
        expected_combinations = {(o, t) for o in expected_outcomes for t in expected_types}
        missing_combinations = expected_combinations - combinations
        
        if missing_combinations:
            print(f"Warning: Missing combinations: {missing_combinations}")
        
        print(f"[OK] Data validation passed!")
        print(f"[OK] {len(self.outcomes_data)} L&D Outcomes")
        print(f"[OK] {len(self.metric_types_data)} Metric Types")
        print(f"[OK] {len(self.metrics_data)} Sample Metrics")
        print(f"[OK] {len(combinations)} out of {len(expected_combinations)} combinations covered")
    
    def check_existing_data(self):
        """Check if data already exists to prevent duplicates."""
        existing_outcomes = LDOutcome.query.count()
        existing_types = MetricType.query.count()
        existing_metrics = Metric.query.count()
        
        if existing_outcomes > 0 or existing_types > 0 or existing_metrics > 0:
            print(f"Existing data found:")
            print(f"  - {existing_outcomes} L&D Outcomes")
            print(f"  - {existing_types} Metric Types")
            print(f"  - {existing_metrics} Metrics")
            
            response = input("Do you want to clear existing data and reseed? (y/N): ").lower()
            if response == 'y':
                return True
            else:
                print("Seeding cancelled to prevent duplicates.")
                return False
        return True
    
    def clear_existing_data(self):
        """Clear all existing data from the database."""
        print("Clearing existing data...")
        Metric.query.delete()
        MetricType.query.delete()
        LDOutcome.query.delete()
        db.session.commit()
        print("[OK] Existing data cleared")
    
    def seed_outcomes(self):
        """Seed L&D Outcomes."""
        print("Seeding L&D Outcomes...")
        for outcome_data in self.outcomes_data:
            outcome = LDOutcome(
                name=outcome_data['name'],
                description=outcome_data['description']
            )
            db.session.add(outcome)
        
        db.session.commit()
        print(f"[OK] {len(self.outcomes_data)} L&D Outcomes seeded")
    
    def seed_metric_types(self):
        """Seed Metric Types."""
        print("Seeding Metric Types...")
        for type_data in self.metric_types_data:
            metric_type = MetricType(
                name=type_data['name'],
                description=type_data['description']
            )
            db.session.add(metric_type)
        
        db.session.commit()
        print(f"[OK] {len(self.metric_types_data)} Metric Types seeded")
    
    def seed_metrics(self):
        """Seed sample metrics."""
        print("Seeding sample metrics...")
        
        # Get outcome and type mappings
        outcomes = {outcome.name: outcome.id for outcome in LDOutcome.query.all()}
        types = {type_.name: type_.id for type_ in MetricType.query.all()}
        
        for metric_data in self.metrics_data:
            metric = Metric(
                name=metric_data['name'],
                description=metric_data['description'],
                example=metric_data['example'],
                outcome_id=outcomes[metric_data['outcome']],
                metric_type_id=types[metric_data['type']]
            )
            db.session.add(metric)
        
        db.session.commit()
        print(f"[OK] {len(self.metrics_data)} sample metrics seeded")
    
    def run_full_seed(self, force=False):
        """Run the complete seeding process."""
        print("=" * 60)
        print("L&D METRICS TRANSLATOR - COMPREHENSIVE DATA SEEDING")
        print("=" * 60)
        
        try:
            # Validate data integrity first
            self.validate_data_integrity()
            
            # Check for existing data
            if not force and not self.check_existing_data():
                return False
            
            # Clear existing data if needed
            if force or LDOutcome.query.count() > 0:
                self.clear_existing_data()
            
            # Seed all data
            self.seed_outcomes()
            self.seed_metric_types()
            self.seed_metrics()
            
            print("\n" + "=" * 60)
            print("[SUCCESS] SEEDING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
            # Print summary
            self.print_summary()
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Error during seeding: {str(e)}")
            db.session.rollback()
            return False
    
    def print_summary(self):
        """Print a summary of seeded data."""
        print("\nDATABASE SUMMARY:")
        print("-" * 40)
        
        outcomes = LDOutcome.query.all()
        for outcome in outcomes:
            metrics_count = outcome.metrics.count()
            print(f"{outcome.name}: {metrics_count} metrics")
        
        print(f"\nTotal Metrics by Type:")
        types = MetricType.query.all()
        for type_ in types:
            metrics_count = Metric.query.filter_by(metric_type_id=type_.id).count()
            print(f"{type_.name}: {metrics_count} metrics")
        
        print(f"\nOverall Total: {Metric.query.count()} metrics")


def main():
    """Main function for command-line interface."""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--force':
            force = True
        elif sys.argv[1] == '--help':
            print("Usage: python seed_data.py [--force] [--help]")
            print("  --force: Clear existing data and reseed without prompting")
            print("  --help:  Show this help message")
            return
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            return
    else:
        force = False
    
    # Initialize the seeder and run
    seeder = DataSeeder()
    success = seeder.run_full_seed(force=force)
    
    if success:
        print("\n[SUCCESS] Ready to test the L&D Metrics Translator!")
        print("You can now run the application and explore the seeded data.")
    else:
        print("\n[ERROR] Seeding failed or was cancelled.")
        sys.exit(1)


if __name__ == '__main__':
    # This allows running the script directly
    from app import create_app
    
    app = create_app()
    with app.app_context():
        main()
