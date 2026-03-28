"""
PDF Generation Service for L&D Metrics Translator
Generates professional reports with metric descriptions, recommendations, and next steps.
"""

import io
import os
import tempfile
import traceback
import re
import copy
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, Frame, PageTemplate
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

from app.models import Metric, LDOutcome, MetricType


class PDFReportGenerator:
    """Professional PDF report generator for L&D metrics analysis."""
    
    def __init__(self):
        self.styles = copy.deepcopy(getSampleStyleSheet())
        self.setup_custom_styles()
        self.page_width = letter[0]
        self.page_height = letter[1]
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles for professional formatting."""
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            spaceBefore=10,
            textColor=colors.HexColor('#34495E'),
            fontName='Helvetica-Bold'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.HexColor('#2980B9'),
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=colors.HexColor('#2980B9'),
            borderPadding=5
        ))
        
        # Metric title style
        self.styles.add(ParagraphStyle(
            name='MetricTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.HexColor('#E74C3C'),
            fontName='Helvetica-Bold'
        ))
        
        # Body text with better spacing
        try:
            body_text = self.styles['BodyText']
            body_text.parent = self.styles['Normal']
            body_text.fontSize = 10
            body_text.spaceAfter = 6
            body_text.alignment = TA_JUSTIFY
            body_text.fontName = 'Helvetica'
        except KeyError:
            self.styles.add(ParagraphStyle(
                name='BodyText',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
                fontName='Helvetica'
            ))
        
        # Recommendation style
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            leftIndent=20,
            bulletIndent=10,
            fontName='Helvetica',
            textColor=colors.HexColor('#27AE60')
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=TA_CENTER
        ))

    def create_header_footer(self, canvas, doc):
        """Create professional header and footer for each page."""
        canvas.saveState()
        
        # Header
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(colors.HexColor('#2C3E50'))
        canvas.drawString(50, doc.height + 50, "L&D Metrics Translator")
        
        # Header line
        canvas.setStrokeColor(colors.HexColor('#2980B9'))
        canvas.setLineWidth(2)
        canvas.line(50, doc.height + 40, doc.width + 50, doc.height + 40)
        
        # Footer
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#7F8C8D'))
        footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        canvas.drawString(50, 30, footer_text)
        
        # Page number
        page_num = f"Page {doc.page}"
        canvas.drawRightString(doc.width + 50, 30, page_num)
        
        canvas.restoreState()

    def generate_metrics_report(self, 
                              selected_metrics: List[Metric],
                              recommendations: Dict[str, Any],
                              user_selections: Dict[str, Any],
                              filename: Optional[str] = None,
                              llm_content: Optional[Dict[str, Any]] = None) -> io.BytesIO:
        """
        Generate a comprehensive PDF report for selected metrics and recommendations.
        
        Args:
            selected_metrics: List of Metric objects
            recommendations: Recommendations data from API
            user_selections: User's filter selections
            filename: Optional filename for the PDF
            
        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = io.BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=100,
            bottomMargin=80
        )
        
        # Build story (content)
        story = []
        
        # Title page
        story.extend(self._create_title_page(user_selections))
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self._create_executive_summary(selected_metrics, recommendations))
        story.append(PageBreak())
        
        # Table of contents placeholder
        story.extend(self._create_table_of_contents())
        story.append(PageBreak())
        
        # Metrics overview
        story.extend(self._create_metrics_overview(selected_metrics))
        story.append(PageBreak())
        
        # Detailed metrics
        story.extend(self._create_detailed_metrics(selected_metrics))
        
        # Recommendations section
        if recommendations:
            story.append(PageBreak())
            story.extend(self._create_recommendations_section(recommendations))
        
        # Implementation roadmap
        story.append(PageBreak())
        story.extend(self._create_implementation_roadmap(selected_metrics, recommendations))
        
        # Appendix
        story.append(PageBreak())
        story.extend(self._create_appendix())
        
        # Build PDF
        doc.build(story, onFirstPage=self.create_header_footer, onLaterPages=self.create_header_footer)
        
        buffer.seek(0)
        return buffer

    def _create_title_page(self, user_selections: Dict[str, Any]) -> List:
        """Create professional title page."""
        story = []
        
        # Main title
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("L&D Metrics Analysis Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Subtitle with selection summary
        selection_summary = self._format_selection_summary(user_selections)
        story.append(Paragraph(f"Analysis for: {selection_summary}", self.styles['Subtitle']))
        story.append(Spacer(1, 1*inch))
        
        # Report metadata table
        metadata = [
            ['Report Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['Report Type:', 'Comprehensive Metrics Analysis'],
            ['Version:', '1.0'],
            ['Tool:', 'L&D Metrics Translator']
        ]
        
        metadata_table = Table(metadata, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 1*inch))
        
        # Disclaimer
        disclaimer = """
        <b>Disclaimer:</b> This report is generated based on your selected metrics and current best practices 
        in Learning & Development analytics. Recommendations should be adapted to your organization's 
        specific context and requirements.
        """
        story.append(Paragraph(disclaimer, self.styles['BodyText']))
        
        return story

    def _create_executive_summary(self, metrics: List[Metric], recommendations: Dict[str, Any]) -> List:
        """Create executive summary section."""
        story = []
        
        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        # Key statistics
        total_metrics = len(metrics)
        metric_types = len(set(m.metric_type.name for m in metrics))
        outcomes = len(set(m.outcome.name for m in metrics))
        
        summary_text = f"""
        This report analyzes <b>{total_metrics} selected metrics</b> across <b>{metric_types} metric categories</b> 
        and <b>{outcomes} L&D outcomes</b>. The analysis provides actionable insights and recommendations 
        to enhance your Learning & Development measurement strategy.
        """
        story.append(Paragraph(summary_text, self.styles['BodyText']))
        story.append(Spacer(1, 20))
        
        # Key insights
        story.append(Paragraph("Key Insights", self.styles['Subtitle']))
        
        insights = [
            f"• {total_metrics} metrics selected for comprehensive L&D measurement",
            f"• {metric_types} different measurement approaches identified",
            f"• {outcomes} business outcomes targeted for improvement",
            "• Balanced approach combining operational, behavioral, and scientific metrics",
            "• Clear implementation roadmap with prioritized recommendations"
        ]
        
        for insight in insights:
            story.append(Paragraph(insight, self.styles['BodyText']))
        
        return story

    def _create_table_of_contents(self) -> List:
        """Create table of contents."""
        story = []
        
        story.append(Paragraph("Table of Contents", self.styles['SectionHeader']))
        
        toc_items = [
            ("Executive Summary", "3"),
            ("Metrics Overview", "4"),
            ("Detailed Metric Analysis", "5"),
            ("Smart Recommendations", "8"),
            ("Implementation Roadmap", "10"),
            ("Appendix", "12")
        ]
        
        toc_data = []
        for item, page in toc_items:
            toc_data.append([item, "." * 50, page])
        
        toc_table = Table(toc_data, colWidths=[3*inch, 2*inch, 0.5*inch])
        toc_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#BDC3C7')),
        ]))
        
        story.append(toc_table)
        
        return story

    def _create_metrics_overview(self, metrics: List[Metric]) -> List:
        """Create metrics overview with charts and statistics."""
        story = []
        
        story.append(Paragraph("Metrics Overview", self.styles['SectionHeader']))
        
        # Metrics by type chart
        type_counts = {}
        outcome_counts = {}
        
        for metric in metrics:
            type_name = metric.metric_type.name
            outcome_name = metric.outcome.name
            
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            outcome_counts[outcome_name] = outcome_counts.get(outcome_name, 0) + 1
        
        # Create metrics distribution table
        story.append(Paragraph("Metrics Distribution by Category", self.styles['Subtitle']))
        
        type_data = [['Metric Category', 'Count', 'Percentage']]
        total = len(metrics)
        
        for type_name, count in type_counts.items():
            percentage = f"{(count/total)*100:.1f}%"
            type_data.append([type_name, str(count), percentage])
        
        type_table = Table(type_data, colWidths=[3*inch, 1*inch, 1*inch])
        type_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980B9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
        ]))
        
        story.append(type_table)
        story.append(Spacer(1, 20))
        
        # Outcomes distribution
        story.append(Paragraph("Metrics Distribution by L&D Outcome", self.styles['Subtitle']))
        
        outcome_data = [['L&D Outcome', 'Count', 'Percentage']]
        for outcome_name, count in outcome_counts.items():
            percentage = f"{(count/total)*100:.1f}%"
            outcome_data.append([outcome_name, str(count), percentage])
        
        outcome_table = Table(outcome_data, colWidths=[3*inch, 1*inch, 1*inch])
        outcome_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
        ]))
        
        story.append(outcome_table)
        
        return story

    def _create_detailed_metrics(self, metrics: List[Metric]) -> List:
        """Create detailed metrics section with full descriptions."""
        story = []
        
        story.append(Paragraph("Detailed Metric Analysis", self.styles['SectionHeader']))
        
        # Group metrics by type
        metrics_by_type = {}
        for metric in metrics:
            type_name = metric.metric_type.name
            if type_name not in metrics_by_type:
                metrics_by_type[type_name] = []
            metrics_by_type[type_name].append(metric)
        
        for type_name, type_metrics in metrics_by_type.items():
            story.append(Paragraph(f"{type_name} Metrics", self.styles['Subtitle']))
            
            for metric in type_metrics:
                # Metric title and outcome
                metric_header = f"{metric.name} ({metric.outcome.name})"
                story.append(Paragraph(metric_header, self.styles['MetricTitle']))
                
                # Description
                if metric.description:
                    story.append(Paragraph(f"<b>Description:</b> {metric.description}", self.styles['BodyText']))
                
                # Example if available
                if metric.example:
                    story.append(Paragraph(f"<b>Example:</b> {metric.example}", self.styles['BodyText']))
                
                # Add some spacing
                story.append(Spacer(1, 10))
        
        return story

    def _create_recommendations_section(self, recommendations: Dict[str, Any]) -> List:
        """Create smart recommendations section."""
        story = []
        
        story.append(Paragraph("Smart Recommendations", self.styles['SectionHeader']))
        
        # Primary recommendations
        if recommendations.get('primary'):
            story.append(Paragraph("Primary Recommendations", self.styles['Subtitle']))
            for rec in recommendations['primary']:
                story.append(Paragraph(f"• <b>{rec.get('title', 'Recommendation')}</b>", self.styles['Recommendation']))
                if rec.get('reasoning'):
                    story.append(Paragraph(f"  {rec['reasoning']}", self.styles['BodyText']))
                if rec.get('metrics'):
                    metrics_text = ", ".join(rec['metrics'])
                    story.append(Paragraph(f"  <i>Key Metrics: {metrics_text}</i>", self.styles['BodyText']))
                story.append(Spacer(1, 8))
        
        # Secondary recommendations
        if recommendations.get('secondary'):
            story.append(Paragraph("Secondary Recommendations", self.styles['Subtitle']))
            for rec in recommendations['secondary']:
                story.append(Paragraph(f"• <b>{rec.get('title', 'Recommendation')}</b>", self.styles['Recommendation']))
                if rec.get('reasoning'):
                    story.append(Paragraph(f"  {rec['reasoning']}", self.styles['BodyText']))
                story.append(Spacer(1, 8))
        
        # Synergies
        if recommendations.get('synergies'):
            story.append(Paragraph("Synergy Opportunities", self.styles['Subtitle']))
            for syn in recommendations['synergies']:
                story.append(Paragraph(f"• <b>{syn.get('title', 'Synergy')}</b>", self.styles['Recommendation']))
                if syn.get('reasoning'):
                    story.append(Paragraph(f"  {syn['reasoning']}", self.styles['BodyText']))
                if syn.get('synergy_score'):
                    score = int(syn['synergy_score'] * 100)
                    story.append(Paragraph(f"  <i>Synergy Score: {score}%</i>", self.styles['BodyText']))
                story.append(Spacer(1, 8))
        
        return story

    def _create_implementation_roadmap(self, metrics: List[Metric], recommendations: Dict[str, Any]) -> List:
        """Create implementation roadmap with timeline and next steps."""
        story = []
        
        story.append(Paragraph("Implementation Roadmap", self.styles['SectionHeader']))
        
        # Phase 1: Foundation (0-3 months)
        story.append(Paragraph("Phase 1: Foundation (0-3 months)", self.styles['Subtitle']))
        phase1_steps = [
            "Establish baseline measurements for selected metrics",
            "Set up data collection processes and tools",
            "Train team on metric definitions and measurement methods",
            "Create initial dashboards and reporting templates"
        ]
        
        for step in phase1_steps:
            story.append(Paragraph(f"• {step}", self.styles['BodyText']))
        
        story.append(Spacer(1, 15))
        
        # Phase 2: Implementation (3-6 months)
        story.append(Paragraph("Phase 2: Implementation (3-6 months)", self.styles['Subtitle']))
        phase2_steps = [
            "Begin regular data collection and analysis",
            "Implement recommended metric combinations",
            "Establish reporting cadence and stakeholder reviews",
            "Refine measurement approaches based on initial results"
        ]
        
        for step in phase2_steps:
            story.append(Paragraph(f"• {step}", self.styles['BodyText']))
        
        story.append(Spacer(1, 15))
        
        # Phase 3: Optimization (6-12 months)
        story.append(Paragraph("Phase 3: Optimization (6-12 months)", self.styles['Subtitle']))
        phase3_steps = [
            "Analyze trends and patterns in collected data",
            "Optimize L&D programs based on metric insights",
            "Expand measurement to additional areas",
            "Develop predictive analytics capabilities"
        ]
        
        for step in phase3_steps:
            story.append(Paragraph(f"• {step}", self.styles['BodyText']))
        
        # Success metrics
        story.append(Spacer(1, 20))
        story.append(Paragraph("Success Metrics for Implementation", self.styles['Subtitle']))
        
        success_data = [
            ['Phase', 'Key Success Indicators', 'Target Timeline'],
            ['Foundation', 'Data collection processes established', '3 months'],
            ['Implementation', 'Regular reporting and analysis', '6 months'],
            ['Optimization', 'Data-driven L&D improvements', '12 months']
        ]
        
        success_table = Table(success_data, colWidths=[1.5*inch, 3*inch, 1.5*inch])
        success_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
        ]))
        
        story.append(success_table)
        
        return story

    def _create_appendix(self) -> List:
        """Create appendix with additional resources."""
        story = []
        
        story.append(Paragraph("Appendix", self.styles['SectionHeader']))
        
        # Glossary
        story.append(Paragraph("Glossary of Terms", self.styles['Subtitle']))
        
        glossary_terms = [
            ("Operational KPI", "Key Performance Indicators focused on business efficiency and ROI"),
            ("Behavioral Metric", "Measurements of human behavior and engagement in learning"),
            ("Neuroscience-Based Metric", "Scientific measurements of cognitive processes and learning effectiveness"),
            ("L&D Outcome", "Desired business results from Learning & Development initiatives"),
            ("Synergy Score", "Measure of how well different metric types complement each other")
        ]
        
        for term, definition in glossary_terms:
            story.append(Paragraph(f"<b>{term}:</b> {definition}", self.styles['BodyText']))
            story.append(Spacer(1, 5))
        
        # Additional resources
        story.append(Spacer(1, 20))
        story.append(Paragraph("Additional Resources", self.styles['Subtitle']))
        
        resources = [
            "• L&D Metrics Translator Documentation",
            "• Best Practices in Learning Analytics",
            "• ROI Calculation Templates",
            "• Data Collection Checklists",
            "• Stakeholder Reporting Templates"
        ]
        
        for resource in resources:
            story.append(Paragraph(resource, self.styles['BodyText']))
        
        return story

    def _format_selection_summary(self, user_selections: Dict[str, Any]) -> str:
        """Format user selections into a readable summary."""
        parts = []
        
        if user_selections.get('categories'):
            parts.append(f"{len(user_selections['categories'])} categories")
        
        if user_selections.get('outcomes'):
            parts.append(f"{len(user_selections['outcomes'])} outcomes")
        
        if user_selections.get('metrics'):
            parts.append(f"{len(user_selections['metrics'])} specific metrics")
        
        if not parts:
            return "All Available Metrics"
        
        return ", ".join(parts)

    def generate_quick_summary(self, metrics: List[Metric]) -> io.BytesIO:
        """Generate a quick 1-page summary report."""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=80,
            bottomMargin=60
        )
        
        story = []
        
        # Title
        story.append(Paragraph("L&D Metrics Quick Summary", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Summary stats
        total_metrics = len(metrics)
        metric_types = len(set((m.metric_type.name if getattr(m, 'metric_type', None) is not None else 'Uncategorized') for m in metrics))
        outcomes = len(set((m.ld_outcome.name if getattr(m, 'ld_outcome', None) is not None else 'Unassigned') for m in metrics))
        
        summary_text = f"""
        <b>Selected Metrics:</b> {total_metrics}<br/>
        <b>Metric Categories:</b> {metric_types}<br/>
        <b>L&D Outcomes:</b> {outcomes}<br/>
        <b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}
        """
        story.append(Paragraph(summary_text, self.styles['BodyText']))
        story.append(Spacer(1, 20))
        
        # Top metrics by type
        metrics_by_type = {}
        for metric in metrics:
            type_name = metric.metric_type.name if getattr(metric, 'metric_type', None) is not None else 'Uncategorized'
            if type_name not in metrics_by_type:
                metrics_by_type[type_name] = []
            metrics_by_type[type_name].append(metric)
        
        for type_name, type_metrics in metrics_by_type.items():
            story.append(Paragraph(f"{type_name}", self.styles['Subtitle']))
            for metric in type_metrics[:3]:  # Show top 3 per type
                story.append(Paragraph(f"• {metric.name}", self.styles['BodyText']))
            story.append(Spacer(1, 10))
        
        doc.build(story, onFirstPage=self.create_header_footer)
        
        buffer.seek(0)
        return buffer

    def generate_comparison_report(self,
                                   a_report: Optional[Dict[str, Any]] = None,
                                   b_report: Optional[Dict[str, Any]] = None,
                                   summary_html: str = '',
                                   key_changes: Optional[List[Dict[str, Any]]] = None) -> io.BytesIO:
        """Generate a compact comparison PDF for two reports.

        Args:
            a_report: dict with keys like {title, date}
            b_report: dict with keys like {title, date}
            summary_html: short HTML snippet summarizing changes
            key_changes: list of {label, change (int), note}
        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=80,
            bottomMargin=60
        )

        story: List[Any] = []

        # Title
        story.append(Paragraph("L&D Comparison Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 8))

        # Report headers table
        a_title = (a_report or {}).get('title') or 'Baseline Report'
        b_title = (b_report or {}).get('title') or 'Follow-up Report'
        a_date = (a_report or {}).get('date') or ''
        b_date = (b_report or {}).get('date') or ''

        hdr_table = Table([
            [Paragraph('<b>Before</b>', self.styles['Subtitle']), Paragraph('<b>After</b>', self.styles['Subtitle'])],
            [Paragraph(a_title, self.styles['BodyText']), Paragraph(b_title, self.styles['BodyText'])],
            [Paragraph(str(a_date), self.styles['BodyText']), Paragraph(str(b_date), self.styles['BodyText'])],
        ], colWidths=[3.25*inch, 3.25*inch])
        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBEFORE', (1, 0), (1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(hdr_table)
        story.append(Spacer(1, 16))

        # Summary
        story.append(Paragraph('Summary of Changes', self.styles['SectionHeader']))
        if summary_html:
            def _sanitize_reportlab_html(html: str) -> str:
                s = (html or '').strip()
                if not s:
                    return ''
                s = s.replace('<strong>', '<b>').replace('</strong>', '</b>')
                s = s.replace('<em>', '<i>').replace('</em>', '</i>')
                s = s.replace('<p>', '').replace('</p>', '<br/><br/>')
                s = s.replace('<div>', '').replace('</div>', '<br/>')
                # Strip all tags except a small allow-list supported by ReportLab's Paragraph
                s = re.sub(r'</?(?!b\b|i\b|u\b|br\b)[^>]*>', '', s, flags=re.IGNORECASE)
                s = re.sub(r'(?:<br\s*/?>\s*){3,}', '<br/><br/>', s, flags=re.IGNORECASE)
                return s

            sanitized = _sanitize_reportlab_html(summary_html)
            try:
                story.append(Paragraph(sanitized, self.styles['BodyText']))
            except Exception:
                # Fallback to plain text if the parser still rejects the input
                plain = re.sub(r'<[^>]+>', '', summary_html)
                story.append(Paragraph(plain, self.styles['BodyText']))
        else:
            story.append(Paragraph('A concise summary of improvements and key movements between baseline and follow-up.', self.styles['BodyText']))
        story.append(Spacer(1, 12))

        # Key changes table
        items = key_changes or []
        if items:
            table_data = [[Paragraph('<b>Metric</b>', self.styles['BodyText']), Paragraph('<b>Change</b>', self.styles['BodyText']), Paragraph('<b>Notes</b>', self.styles['BodyText'])]]
            for it in items:
                label = str(it.get('label') or '')
                change = it.get('change')
                note = str(it.get('note') or '')
                change_str = f"{('+' if isinstance(change, (int, float)) and change>0 else '')}{change}%" if change is not None else '—'
                table_data.append([label, change_str, note])
            chg_table = Table(table_data, colWidths=[2.5*inch, 1.0*inch, 3.0*inch])
            chg_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980B9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
            ]))
            story.append(chg_table)
        else:
            story.append(Paragraph('No key changes identified.', self.styles['BodyText']))

        story.append(Spacer(1, 18))
        story.append(Paragraph('Generated by L&D Metrics Translator', self.styles['Footer']))

        doc.build(story, onFirstPage=self.create_header_footer)
        buffer.seek(0)
        return buffer
