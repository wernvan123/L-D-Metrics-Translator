"""
Dynamic PDF Report Generation Service

This service handles the generation of context-aware PDF reports based on:
- Selected L&D outcomes
- Selected metrics by category
- AI recommendations
- User session context
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY
import os

from app.models import (
    DynamicReport, ReportTemplate, ReportAnalytics,
    LDOutcome, Metric
)
from app import db


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    title: str
    template_type: str  # 'comprehensive' or 'basic'
    selected_outcomes: List[int]
    selected_metrics: List[int]
    ai_recommendations: List[Dict]
    session_id: str
    generation_context: Dict


class DynamicReportGenerator:
    """Main service for generating dynamic PDF reports."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for reports."""
        self.styles.add(ParagraphStyle(
            name='ExecutiveTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            textColor=HexColor('#2C3E50'),
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=20,
            textColor=HexColor('#34495E'),
            fontName='Helvetica-Bold'
        ))
        
        # Use a unique name to avoid clashing with built-in 'BodyText'
        self.styles.add(ParagraphStyle(
            name='BodyTextCustom',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))

    def generate_report(self, config: ReportConfig) -> DynamicReport:
        """Generate a complete dynamic PDF report."""
        start_time = time.time()
        
        # Get or create report template
        template = self._get_template(config.template_type)
        
        # Create report record
        report = DynamicReport.create_report(
            title=config.title,
            template_id=template.id,
            session_id=config.session_id,
            selected_outcomes=config.selected_outcomes,
            selected_metrics=config.selected_metrics,
            ai_recommendations=config.ai_recommendations,
            generation_context=config.generation_context
        )
        
        try:
            # Update status to generating
            report.update_progress(5, 'generating')
            
            # Analyze selections for content adaptation
            analysis = self._analyze_selections(config)
            report.update_progress(15)
            
            # Generate content sections
            content = self._generate_content(config, analysis)
            report.update_progress(50)
            
            # Update report with generated content
            self._update_report_content(report, content)
            report.update_progress(60)
            
            # Generate PDF
            pdf_path, file_size, page_count = self._generate_pdf(report, content, config)
            report.update_progress(90)
            
            # Create analytics
            self._create_analytics(report, analysis)
            
            # Mark as completed
            generation_time = int((time.time() - start_time) * 1000)
            report.mark_completed(pdf_path, file_size, page_count, generation_time)
            
            return report
            
        except Exception as e:
            report.mark_failed(str(e))
            raise

    def _get_template(self, template_type: str) -> ReportTemplate:
        """Get or create report template."""
        template = ReportTemplate.query.filter_by(
            template_type=template_type,
            is_active=True
        ).first()
        
        if not template:
            template = self._create_default_template(template_type)
            
        return template

    def _create_default_template(self, template_type: str) -> ReportTemplate:
        """Create default template configuration."""
        if template_type == 'comprehensive':
            sections = [
                {"type": "executive_summary", "title": "Executive Summary", "pages": 1, "order": 1},
                {"type": "strategy_context", "title": "L&D Strategy Context", "pages": 3, "order": 2},
                {"type": "metric_analysis", "title": "Metric Portfolio Analysis", "pages": 4, "order": 3},
                {"type": "ai_insights", "title": "AI-Enhanced Recommendations", "pages": 3, "order": 4},
                {"type": "implementation_roadmap", "title": "Implementation Roadmap", "pages": 4, "order": 5},
                {"type": "success_metrics", "title": "Success Metrics & Monitoring", "pages": 2, "order": 6},
                {"type": "appendices", "title": "Appendices", "pages": 3, "order": 7}
            ]
        elif template_type == 'final_plan':
            # Five-section Final Developmental Plan outline
            sections = [
                {"type": "final_executive_context", "title": "Executive Summary & Context", "pages": 1, "order": 1},
                {"type": "visual_synthesis", "title": "Visual Synthesis", "pages": 1, "order": 2},
                {"type": "gap_analysis", "title": "Detailed Gap Analysis & Driver Breakdown", "pages": 2, "order": 3},
                {"type": "interventions_nudges", "title": "Actionable Interventions & Nudges", "pages": 2, "order": 4},
                {"type": "action_plan_next_steps", "title": "Action Plan & Next Steps", "pages": 2, "order": 5},
            ]
        else:  # basic
            sections = [
                {"type": "executive_summary", "title": "Executive Summary", "pages": 1, "order": 1},
                {"type": "metric_analysis", "title": "Selected Metrics Analysis", "pages": 3, "order": 2},
                {"type": "ai_insights", "title": "AI Recommendations", "pages": 2, "order": 3},
                {"type": "implementation_roadmap", "title": "Implementation Plan", "pages": 3, "order": 4},
                {"type": "success_metrics", "title": "Resource Requirements", "pages": 1, "order": 5}
            ]
        
        styling = {
            "colors": {"primary": "#2C3E50", "secondary": "#34495E", "accent": "#E74C3C"},
            "fonts": {"heading": "Helvetica-Bold", "body": "Helvetica"}
        }
        
        template = ReportTemplate(
            name=f"{template_type.title()} Report Template",
            description=f"Default {template_type} report template with dynamic content adaptation",
            template_type=template_type,
            sections=json.dumps(sections),
            styling=json.dumps(styling)
        )
        
        db.session.add(template)
        db.session.commit()
        return template

    def _analyze_selections(self, config: ReportConfig) -> Dict:
        """Analyze user selections to determine content adaptation strategy."""
        analysis = {
            'outcome_focus': {},
            'metric_distribution': {},
            'ai_recommendation_complexity': len(config.ai_recommendations),
            'estimated_pages': 0,
            'content_weights': {},
            'implementation_complexity': 0
        }
        
        # Analyze outcome distribution
        outcomes = LDOutcome.query.filter(LDOutcome.id.in_(config.selected_outcomes)).all()
        for outcome in outcomes:
            analysis['outcome_focus'][outcome.name] = {
                'id': outcome.id,
                'description': outcome.description
            }
        
        # Analyze metric type distribution
        metrics = Metric.query.filter(Metric.id.in_(config.selected_metrics)).all()
        metric_types = {}
        for metric in metrics:
            type_name = metric.metric_type.name
            if type_name not in metric_types:
                metric_types[type_name] = []
            metric_types[type_name].append(metric)
        
        analysis['metric_distribution'] = {
            type_name: {
                'count': len(metrics_list),
                'metrics': [m.to_dict() for m in metrics_list]
            }
            for type_name, metrics_list in metric_types.items()
        }
        
        # Calculate content weights
        total_metrics = len(config.selected_metrics)
        operational_count = len(metric_types.get('Operational KPI', []))
        behavioral_count = len(metric_types.get('Behavioral Metric', []))
        neuroscience_count = len(metric_types.get('Neuroscience-Based Metric', []))
        
        analysis['content_weights'] = {
            'roi_focus': operational_count / total_metrics if total_metrics > 0 else 0,
            'change_management': behavioral_count / total_metrics if total_metrics > 0 else 0,
            'scientific_backing': neuroscience_count / total_metrics if total_metrics > 0 else 0,
            'ai_integration': min(1.0, len(config.ai_recommendations) / 10)
        }
        
        # Estimate complexity and pages
        base_pages = 8 if config.template_type == 'comprehensive' else 5
        complexity_modifier = (operational_count * 0.5 + behavioral_count * 0.7 + neuroscience_count * 1.0) / 10
        
        analysis['estimated_pages'] = int(base_pages + (base_pages * complexity_modifier))
        analysis['implementation_complexity'] = min(1.0, complexity_modifier)
        
        return analysis

    def _generate_content(self, config: ReportConfig, analysis: Dict) -> Dict:
        """Generate dynamic content for each report section."""
        content = {}
        
        if config.template_type == 'final_plan':
            # New five-section Final Developmental Plan
            content['final_executive_context'] = self._generate_final_executive_context(config, analysis)
            content['visual_synthesis'] = self._generate_visual_synthesis(config, analysis)
            content['gap_analysis'] = self._generate_gap_analysis_driver_breakdown(config, analysis)
            content['interventions_nudges'] = self._generate_interventions_nudges(config, analysis)
            content['action_plan_next_steps'] = self._generate_action_plan_table(config, analysis)
        else:
            content['executive_summary'] = self._generate_executive_summary(config, analysis)
            
            if config.template_type == 'comprehensive':
                content['strategy_context'] = self._generate_strategy_context(config, analysis)
            
            content['metric_analysis'] = self._generate_metric_analysis(config, analysis)
            content['ai_insights'] = self._generate_ai_insights(config, analysis)
            content['implementation_roadmap'] = self._generate_implementation_roadmap(config, analysis)
            content['success_metrics'] = self._generate_success_metrics(config, analysis)
            
            if config.template_type == 'comprehensive':
                content['appendices'] = self._generate_appendices(config, analysis)
        
        return content

    def _generate_executive_summary(self, config: ReportConfig, analysis: Dict) -> str:
        """Generate executive summary based on selections."""
        outcomes_text = ", ".join(analysis['outcome_focus'].keys())
        metric_count = len(config.selected_metrics)
        ai_count = len(config.ai_recommendations)
        
        readiness_score = int((1 - analysis['implementation_complexity']) * 100)
        
        return f"""Strategic Overview: This report focuses on {outcomes_text} with {metric_count} selected metrics.

Key Findings:
• {metric_count} metrics across {len(analysis['metric_distribution'])} categories
• {ai_count} AI-enhanced recommendations
• Implementation complexity: {'Low' if analysis['implementation_complexity'] < 0.3 else 'Medium' if analysis['implementation_complexity'] < 0.7 else 'High'}

Implementation Readiness Score: {readiness_score}%

Expected Outcomes: Implementation will provide actionable insights into {outcomes_text.lower()}, enabling data-driven L&D decision making."""

    def _generate_strategy_context(self, config: ReportConfig, analysis: Dict) -> str:
        """Generate L&D strategy context section."""
        content = "Selected Outcomes Analysis:\n"
        for outcome_name, outcome_data in analysis['outcome_focus'].items():
            content += f"\n{outcome_name}: {outcome_data['description']}\n"
        
        content += f"\nOrganizational Alignment: Your selection shows {int(analysis['content_weights']['roi_focus'] * 100)}% focus on operational KPIs."
        
        complexity = analysis['implementation_complexity']
        approach = 'Rapid deployment' if complexity < 0.3 else 'Phased implementation' if complexity < 0.7 else 'Comprehensive change management'
        content += f"\nRecommended approach: {approach}"
        
        return content

    def _generate_metric_analysis(self, config: ReportConfig, analysis: Dict) -> str:
        """Generate detailed metric analysis section."""
        content = "Selected Metrics Deep Dive:\n"
        
        for metric_type, type_data in analysis['metric_distribution'].items():
            content += f"\n{metric_type} ({type_data['count']} metrics):\n"
            for metric in type_data['metrics'][:2]:
                content += f"• {metric['name']}: {metric['description'][:150]}...\n"
        
        total_metrics = len(config.selected_metrics)
        content += f"\nPortfolio Distribution: {total_metrics} total metrics selected"
        
        return content

    def _generate_ai_insights(self, config: ReportConfig, analysis: Dict) -> str:
        """Generate AI recommendations section."""
        ai_count = len(config.ai_recommendations)
        
        if ai_count > 0:
            content = f"Smart AI Suggestions ({ai_count} recommendations):\n"
            for i, rec in enumerate(config.ai_recommendations[:3], 1):
                content += f"\n{i}. {rec.get('title', 'AI Recommendation')}: {rec.get('description', 'Advanced measurement concept.')}\n"
            
            content += f"\nThe AI recommendations complement your selected metrics with {ai_count} additional opportunities."
        else:
            content = "AI-Enhanced Analysis: Your metric selection demonstrates strong alignment with best practices."
        
        return content

    def _generate_implementation_roadmap(self, config: ReportConfig, analysis: Dict) -> str:
        """Generate implementation roadmap section."""
        complexity = analysis['implementation_complexity']
        
        content = "Phase 1: Foundation (0-3 months)\n"
        content += "• Implement operational KPI measurement\n"
        content += "• Establish basic infrastructure\n"
        
        content += "\nPhase 2: Behavioral Integration (3-9 months)\n"
        content += "• Deploy behavioral metric tracking\n"
        content += "• Implement change management strategies\n"
        
        if complexity > 0.3:
            content += "\nPhase 3: Advanced Analytics (9-18 months)\n"
            content += "• Integrate neuroscience-based metrics\n"
            if len(config.ai_recommendations) > 0:
                content += f"• Implement {min(3, len(config.ai_recommendations))} AI recommendations\n"
        
        budget = '$50K-100K' if complexity < 0.3 else '$100K-250K' if complexity < 0.7 else '$250K+'
        content += f"\nResource Requirements:\n• Budget: {budget} (estimated)\n• Personnel: {2 if complexity < 0.3 else 4 if complexity < 0.7 else 6}+ team members"
        
        return content

    def _generate_success_metrics(self, config: ReportConfig, analysis: Dict) -> str:
        """Generate success metrics and monitoring section."""
        content = "KPI Dashboard Design:\n"
        for outcome_name in analysis['outcome_focus'].keys():
            content += f"• {outcome_name} tracking panel\n"
        
        content += f"• {len(config.selected_metrics)} metric visualization widgets\n"
        
        content += "\nReporting Cadence:\n"
        content += "• Daily: Operational KPI monitoring\n"
        content += "• Weekly: Behavioral metric trends\n"
        content += "• Monthly: Comprehensive outcome analysis\n"
        content += "• Quarterly: Strategic alignment review\n"
        
        return content

    def _generate_appendices(self, config: ReportConfig, analysis: Dict) -> str:
        """Generate appendices section."""
        content = "Detailed Metric Definitions:\n"
        
        for metric_type, type_data in analysis['metric_distribution'].items():
            content += f"\n{metric_type}:\n"
            for metric in type_data['metrics']:
                content += f"• {metric['name']}: {metric['description']}\n"
        
        content += "\nImplementation Templates:\n"
        content += "• Metric collection checklists\n"
        content += "• Data validation procedures\n"
        content += "• Progress tracking spreadsheets\n"
        
        return content

    def _update_report_content(self, report: DynamicReport, content: Dict):
        """Update report with generated content."""
        # For backward compatibility, map new final_plan sections into existing fields where possible
        if 'final_executive_context' in content:
            report.executive_summary = content.get('final_executive_context', '')
            report.strategy_context = content.get('visual_synthesis', '')
            report.metric_analysis = content.get('gap_analysis', '')
            report.ai_insights = content.get('interventions_nudges', '')
            # action_plan_next_steps may include table data; store a simple textual summary
            plan = content.get('action_plan_next_steps', {}) or {}
            if isinstance(plan, dict):
                intro = plan.get('intro', '')
                rows = plan.get('rows', [])
                rows_count = len(rows) if isinstance(rows, list) else 0
                report.implementation_roadmap = f"{intro}\n\nItems: {rows_count}"
            else:
                report.implementation_roadmap = str(plan)
            report.success_metrics = ''
            report.appendices = ''
        else:
            report.executive_summary = content.get('executive_summary', '')
            report.strategy_context = content.get('strategy_context', '')
            report.metric_analysis = content.get('metric_analysis', '')
            report.ai_insights = content.get('ai_insights', '')
            report.implementation_roadmap = content.get('implementation_roadmap', '')
            report.success_metrics = content.get('success_metrics', '')
            report.appendices = content.get('appendices', '')
        db.session.commit()

    def _generate_pdf(self, report: DynamicReport, content: Dict, config: ReportConfig) -> Tuple[str, int, int]:
        """Generate PDF file from content."""
        # Save under the app's static directory so Flask can serve /static/reports/*.pdf
        # __file__ -> .../ld-metrics-translator/app/services/report_generator.py
        # dirname(__file__) -> .../ld-metrics-translator/app/services
        # dirname(dirname(__file__)) -> .../ld-metrics-translator/app
        # dirname(dirname(dirname(__file__))) -> .../ld-metrics-translator
        app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        reports_dir = os.path.join(app_root, 'static', 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{report.id}_{timestamp}.pdf"
        pdf_path = os.path.join(reports_dir, filename)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        story = []
        
        # Title page
        story.append(Paragraph(report.title, self.styles['ExecutiveTitle']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal']))
        story.append(Spacer(1, 0.5*inch))
        
        # Add content sections
        if config.template_type == 'final_plan':
            sections = [
                ('Executive Summary & Context', content.get('final_executive_context', '')),
                ('Visual Synthesis', content.get('visual_synthesis', '')),
                ('Detailed Gap Analysis & Driver Breakdown', content.get('gap_analysis', '')),
                ('Actionable Interventions & Nudges', content.get('interventions_nudges', '')),
                ('Action Plan & Next Steps', content.get('action_plan_next_steps', '')),
            ]
        else:
            sections = [
                ('Executive Summary', content.get('executive_summary', '')),
                ('L&D Strategy Context', content.get('strategy_context', '')),
                ('Metric Portfolio Analysis', content.get('metric_analysis', '')),
                ('AI-Enhanced Recommendations', content.get('ai_insights', '')),
                ('Implementation Roadmap', content.get('implementation_roadmap', '')),
                ('Success Metrics & Monitoring', content.get('success_metrics', '')),
                ('Appendices', content.get('appendices', ''))
            ]
        
        for section_title, section_content in sections:
            if section_content:
                story.append(PageBreak())
                story.append(Paragraph(section_title, self.styles['SectionHeader']))
                story.append(Spacer(1, 0.1*inch))
                
                # Handle dict content (e.g., action plan table) or string paragraphs
                if isinstance(section_content, dict) and section_title == 'Action Plan & Next Steps':
                    intro = section_content.get('intro', '')
                    if intro:
                        story.append(Paragraph(intro.strip(), self.styles['BodyTextCustom']))
                        story.append(Spacer(1, 0.1*inch))
                    headers = section_content.get('table_headers', ['Priority', 'Driver', 'Nudge/Intervention', 'Owner', 'Timeline'])
                    rows = section_content.get('rows', [])
                    data = [headers] + rows
                    table = Table(data, hAlign='LEFT')
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), HexColor('#ecf0f1')),
                        ('TEXTCOLOR', (0,0), (-1,0), HexColor('#2C3E50')),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), 9),
                        ('BOTTOMPADDING', (0,0), (-1,0), 6),
                        ('BACKGROUND', (0,1), (-1,-1), HexColor('#ffffff')),
                        ('GRID', (0,0), (-1,-1), 0.25, HexColor('#bdc3c7')),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.1*inch))
                else:
                    # Add content paragraphs
                    paragraphs = str(section_content).split('\n\n')
                    for para in paragraphs:
                        if para.strip():
                            story.append(Paragraph(para.strip(), self.styles['BodyTextCustom']))
                            story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        
        # Get file info
        file_size = os.path.getsize(pdf_path)
        page_count = len(story) // 10  # Rough estimate
        
        return pdf_path, file_size, page_count

    # -------------------------------
    # New Final Developmental Plan builders
    # -------------------------------
    def _get_context(self, config: ReportConfig) -> Dict:
        """Helper to safely extract extended context from generation_context."""
        ctx = config.generation_context or {}
        return {
            'role_profile': ctx.get('role_profile') or {},
            'framework_focus': ctx.get('framework_focus') or {},
            'target_outcome': ctx.get('target_outcome') or {},
            'drivers': ctx.get('drivers') or [],
            'nudges': ctx.get('nudges') or [],
            'proficiency': ctx.get('proficiency') or {},
        }

    def _generate_final_executive_context(self, config: ReportConfig, analysis: Dict) -> str:
        ctx = self._get_context(config)
        role_name = ctx['role_profile'].get('name') or 'Target Role'
        framework_name = ctx['framework_focus'].get('name') or ctx['framework_focus'].get('slug') or 'Selected Framework'
        outcome_name = ctx['target_outcome'].get('name') or ", ".join(analysis['outcome_focus'].keys()) or 'Outcome Focus'
        readiness_score = int((1 - analysis['implementation_complexity']) * 100)
        return (
            f"Role Profile: {role_name}\n\n"
            f"Framework Focus: {framework_name}\n\n"
            f"Target Outcome: {outcome_name}\n\n"
            f"Summary: This plan prioritizes measurable progress across selected drivers and nudges aligned to {framework_name}.\n\n"
            f"Implementation Readiness: {readiness_score}%"
        )

    def _generate_visual_synthesis(self, config: ReportConfig, analysis: Dict) -> str:
        ctx = self._get_context(config)
        prof = ctx['proficiency'] or {}
        if prof.get('radar') or prof.get('tree'):
            return (
                "Visual Synthesis Overview:\n\n"
                "Provided proficiency data will be visualized as a radar/tree diagram highlighting current vs. target levels."
            )
        return (
            "Visual Synthesis Placeholder:\n\n"
            "Charts will be incorporated when proficiency data is provided (e.g., radar across competencies or driver tree)."
        )

    def _generate_gap_analysis_driver_breakdown(self, config: ReportConfig, analysis: Dict) -> str:
        ctx = self._get_context(config)
        prof = ctx['proficiency'] or {}
        items = []
        # Expecting prof like {'competencies': [{'name':..., 'current': x, 'target': y}, ...]}
        comps = (prof.get('competencies') or []) if isinstance(prof, dict) else []
        for c in comps[:10]:
            name = c.get('name', 'Competency')
            cur = c.get('current')
            tgt = c.get('target')
            if isinstance(cur, (int, float)) and isinstance(tgt, (int, float)):
                gap = round(tgt - cur, 2)
                items.append(f"• {name}: current {cur} → target {tgt} (gap {gap})")
        if not items:
            items.append("• Gaps will be calculated once proficiency benchmarks are provided.")
        drivers = ctx['drivers'] or []
        driver_summary = f"Drivers selected: {', '.join([d.get('name','Driver') for d in drivers[:6]])}" if drivers else "No explicit drivers provided yet."
        return "Detailed Gaps:\n" + "\n".join(items) + "\n\n" + driver_summary

    def _generate_interventions_nudges(self, config: ReportConfig, analysis: Dict) -> str:
        ctx = self._get_context(config)
        nudges = ctx['nudges'] or []
        if not nudges:
            return (
                "Interventions & Nudges:\n\n"
                "No nudges provided. We recommend starting with small, context-specific prompts aligned to drivers."
            )
        lines = [
            "Interventions & Nudges:\n",
        ]
        for i, n in enumerate(nudges[:10], 1):
            title = n.get('title') or n.get('name') or f'Nudge {i}'
            desc = n.get('description') or n.get('details') or ''
            lines.append(f"{i}. {title}: {desc}")
        return "\n".join(lines)

    def _generate_action_plan_table(self, config: ReportConfig, analysis: Dict) -> Dict:
        ctx = self._get_context(config)
        drivers = ctx['drivers'] or []
        nudges = ctx['nudges'] or []
        # Construct simple action rows pairing drivers with nudges when possible
        rows = []
        max_len = max(len(drivers), len(nudges), 0)
        for i in range(max_len):
            d = drivers[i] if i < len(drivers) else {}
            n = nudges[i] if i < len(nudges) else {}
            priority = n.get('priority') or d.get('priority') or ('High' if i < 3 else 'Medium' if i < 6 else 'Low')
            driver_name = d.get('name') or d.get('title') or '—'
            nudge_name = n.get('title') or n.get('name') or '—'
            owner = n.get('owner') or d.get('owner') or 'L&D Lead'
            timeline = n.get('timeline') or d.get('timeline') or '0-90 days'
            rows.append([priority, driver_name, nudge_name, owner, timeline])
        intro = (
            "This action plan sequences near-term interventions mapped to selected drivers. "
            "Owners and timelines are suggested and should be tailored to local context."
        )
        headers = ['Priority', 'Driver', 'Nudge/Intervention', 'Owner', 'Timeline']
        return {'intro': intro, 'table_headers': headers, 'rows': rows}

    def _create_analytics(self, report: DynamicReport, analysis: Dict):
        """Create analytics entry for the report."""
        ReportAnalytics.create_analytics(
            report_id=report.id,
            outcome_distribution=analysis['outcome_focus'],
            metric_type_distribution=analysis['metric_distribution'],
            ai_recommendation_count=analysis['ai_recommendation_complexity'],
            complexity_score=analysis['implementation_complexity']
        )
