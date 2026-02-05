# User Guide

Welcome to the L&D Metrics Translator! This comprehensive guide will help you navigate and make the most of this powerful tool for translating learning outcomes into measurable business metrics.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Navigation Overview](#navigation-overview)
3. [Exploring Metrics](#exploring-metrics)
4. [Filtering and Search](#filtering-and-search)
5. [Metric Details](#metric-details)
6. [Diagnostics (Human Performance Navigator)](#diagnostics-human-performance-navigator)
7. [Admin Features](#admin-features)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Getting Started

### Accessing the Application

1. **Open your web browser** and navigate to the application URL
2. **Homepage Overview**: You'll see the main dashboard with metrics overview
3. **No login required** for browsing metrics (admin features require authentication)

![Homepage Screenshot](../screenshots/homepage.png)
*The L&D Metrics Translator homepage showing the main navigation and metrics overview*

### First Steps

1. **Explore the metrics database** using the main navigation
2. **Try the search functionality** to find specific metrics
3. **Use filters** to narrow down metrics by category
4. **Click on metrics** to view detailed information

## Navigation Overview

### Main Navigation Bar

The top navigation provides access to key sections:

- **Home** (🏠): Return to the main dashboard
- **All Metrics**: Browse the complete metrics database
- **Outcomes**: View metrics by L&D outcomes
- **Types**: Browse by metric types
- **Search** (🔍): Advanced search functionality
- **Diagnostics**: Event Analysis and behavioral diagnostics
- **Admin** (👤): Administrative features (login required)

![Navigation Screenshot](../screenshots/navigation.png)
*Main navigation bar showing all available sections*

### Quick Stats Dashboard

The homepage displays key statistics:
- **Total Metrics**: Complete count of available metrics
- **L&D Outcomes**: Number of outcome categories
- **Metric Types**: Available metric type classifications
- **Recent Updates**: Latest additions to the database

## Exploring Metrics

### Metrics Overview

The metrics database contains comprehensive information about L&D measurement approaches, organized by:

- **L&D Outcomes**: The learning objectives you want to achieve
- **Metric Types**: The category of measurement approach
- **Practical Examples**: Real-world applications and use cases

![Metrics Overview Screenshot](../screenshots/metrics-overview.png)
*Metrics overview page showing the complete database with filtering options*

### Understanding L&D Outcomes

The application organizes metrics by five key L&D outcomes:

1. **Engagement** 📈
   - Employee satisfaction and motivation
   - Participation rates in learning programs
   - Feedback scores and sentiment analysis

2. **Retention** 🎯
   - Employee turnover reduction
   - Knowledge retention rates
   - Long-term skill application

3. **Behavior Change** 🔄
   - Observable workplace behaviors
   - Skill application in real scenarios
   - Performance improvements

4. **Performance** 🚀
   - Productivity metrics
   - Quality improvements
   - Goal achievement rates

5. **Well-being** 💚
   - Work-life balance indicators
   - Stress reduction measures
   - Health and wellness metrics

### Metric Types Explained

Each metric is classified by type to help you choose the right measurement approach:

1. **Operational KPI** 📊
   - Quantitative business metrics
   - Measurable performance indicators
   - ROI and efficiency measures

2. **Behavioral Metric** 👥
   - Observable actions and behaviors
   - Skill demonstration indicators
   - Interaction and collaboration measures

3. **Neuroscience Concept** 🧠
   - Science-backed measurement approaches
   - Cognitive and emotional indicators
   - Research-validated assessment methods

## Filtering and Search

### Using Filters

![Filters Screenshot](../screenshots/filters.png)
*Filter interface showing outcome and type selection options*

1. **Outcome Filter**:
   - Select one or more L&D outcomes
   - Instantly updates the metrics display
   - Clear filters to reset view

2. **Type Filter**:
   - Choose specific metric types
   - Combine with outcome filters for precise results
   - Visual indicators show active filters

3. **Combined Filtering**:
   - Use multiple filters simultaneously
   - Results update in real-time
   - Filter count displays in the interface

### Search Functionality

![Search Screenshot](../screenshots/search.png)
*Advanced search interface with results highlighting*

The search feature provides powerful text-based discovery:

1. **Search Box**:
   - Enter keywords related to your needs
   - Searches across metric names, descriptions, and examples
   - Real-time suggestions as you type

2. **Search Results**:
   - Highlighted matching terms
   - Relevance-based ordering
   - Quick preview of metric information

3. **Search Tips**:
   - Use specific terms for better results
   - Try different synonyms
   - Combine with filters for precision

### Advanced Search Techniques

- **Exact phrases**: Use quotes for exact matches ("employee engagement")
- **Multiple terms**: Space-separated terms find metrics containing all words
- **Category search**: Include outcome or type names in your search
- **Example search**: Search within practical examples for use cases

## Metric Details

### Viewing Detailed Information

Click on any metric to access comprehensive details:

![Metric Detail Screenshot](../screenshots/metric-detail.png)
*Detailed metric view showing all available information*

### Metric Detail Components

1. **Metric Name**: Clear, descriptive title
2. **Description**: Comprehensive explanation of what the metric measures
3. **Practical Example**: Real-world application scenarios
4. **L&D Outcome**: Associated learning objective category
5. **Metric Type**: Classification of measurement approach
6. **Related Metrics**: Suggestions for complementary measurements

### Using Metric Information

**For L&D Professionals**:
- Understand what each metric measures
- See practical implementation examples
- Identify metrics that align with your program goals
- Build comprehensive measurement frameworks

**For Stakeholders**:
- Connect learning initiatives to business outcomes
- Understand the value and impact of L&D programs
- Make data-driven decisions about learning investments
- Communicate ROI effectively

## Diagnostics (Human Performance Navigator)

The Diagnostics area supports consultant-led analysis of workplace events and patterns.

### Accessing Diagnostics

- Navigate to: `/diagnostics`
- Use this area to analyze an event description and generate structured insights.

### Event Analysis workflow

1. Enter a workplace event description in the text box.
2. (Optional) Select a Role Profile to contextualize the analysis.
3. Click **Analyze Event**.

Notes:
- Anonymous usage is supported.
- If a Role Profile is selected, the output may include role-contextualized insights (gap analysis).

### Consultant operating model

Diagnostics is designed to support consulting engagements where:
- You (the consultant) run the analysis and interpret findings.
- The company provides access to the relevant data sources and/or exports.
- Outputs should be reviewed with stakeholders at an appropriate aggregation level.

### MVP direction: company data intake via exports

For early pilots, the intended data intake approach is exports/CSV-first from the systems a company already uses (examples):

- Work tracking / project systems (tickets, cycle times, blocked reasons)
- Retrospectives (themes, action items)
- Code repository / pull request activity (optional)
- Survey exports (engagement, feedback)

This enables event feeds and diagnostics without requiring employees to manually log every event. CSV ingestion may be introduced incrementally depending on the deployment.

## Admin Features

### Accessing Admin Panel

![Admin Login Screenshot](../screenshots/admin-login.png)
*Admin login interface for accessing management features*

1. **Login Process**:
   - Click "Admin" in the main navigation
   - Enter your admin credentials
   - Access the administrative dashboard

2. **Admin Dashboard**:
   - Overview of system statistics
   - Quick access to management functions
   - Recent activity monitoring

### Content Management

![Admin Dashboard Screenshot](../screenshots/admin-dashboard.png)
*Admin dashboard showing content management options*

**Metrics Management**:
- Add new metrics to the database
- Edit existing metric information
- Delete outdated or incorrect metrics
- Bulk import/export functionality

**Category Management**:
- Manage L&D outcome categories
- Update metric type classifications
- Organize and restructure content

**User Management**:
- Create and manage admin accounts
- Set user permissions and roles
- Monitor user activity and access

### Data Import/Export

**Import Features**:
- CSV file import for bulk metric addition
- Data validation and error checking
- Preview before committing changes

**Export Features**:
- Export metrics database to CSV
- Generate reports and analytics
- Backup data for archival purposes

## Best Practices

### For L&D Professionals

1. **Start with Outcomes**:
   - Identify your primary L&D objectives
   - Use outcome filters to find relevant metrics
   - Build a balanced measurement approach

2. **Combine Metric Types**:
   - Use operational KPIs for business impact
   - Include behavioral metrics for skill application
   - Consider neuroscience concepts for deeper insights

3. **Create Measurement Frameworks**:
   - Select 3-5 key metrics per program
   - Ensure metrics align with business goals
   - Plan for both short-term and long-term measurement

### For Stakeholder Communication

1. **Business Language**:
   - Focus on operational KPIs for executive discussions
   - Use concrete examples and case studies
   - Connect learning metrics to business outcomes

2. **Visual Presentation**:
   - Create dashboards with key metrics
   - Use charts and graphs for impact visualization
   - Tell the story behind the numbers

3. **Regular Reporting**:
   - Establish consistent measurement cycles
   - Track trends over time
   - Celebrate successes and address challenges

### Implementation Tips

1. **Baseline Measurement**:
   - Establish baseline metrics before program launch
   - Document current state for comparison
   - Set realistic improvement targets

2. **Data Collection**:
   - Plan data collection methods in advance
   - Ensure data quality and consistency
   - Use multiple sources for validation

3. **Continuous Improvement**:
   - Regularly review and adjust metrics
   - Gather feedback from stakeholders
   - Evolve measurement approaches based on learning

## Troubleshooting

### Common Issues

**Search Not Working**:
- Check your internet connection
- Try simpler search terms
- Clear browser cache and cookies
- Contact support if issues persist

**Filters Not Responding**:
- Refresh the page
- Ensure JavaScript is enabled
- Try a different browser
- Report persistent issues

**Page Loading Slowly**:
- Check internet connection speed
- Close unnecessary browser tabs
- Clear browser cache
- Try during off-peak hours

### Browser Compatibility

**Supported Browsers**:
- Chrome 90+ (recommended)
- Firefox 88+
- Safari 14+
- Edge 90+

**Mobile Devices**:
- iOS Safari 14+
- Android Chrome 90+
- Responsive design adapts to screen size

### Getting Help

**Self-Service Resources**:
- This user guide
- FAQ section on the website
- Video tutorials (coming soon)
- Community forum discussions

**Contact Support**:
- Email: support@ldmetrics.com
- Response time: 24-48 hours
- Include screenshots for visual issues
- Provide browser and device information

**Feature Requests**:
- Submit via GitHub issues
- Email suggestions to feedback@ldmetrics.com
- Participate in user surveys
- Join beta testing programs

## Tips for Success

### Maximizing Value

1. **Regular Exploration**:
   - Check for new metrics monthly
   - Explore different outcome categories
   - Stay updated with latest additions

2. **Team Collaboration**:
   - Share interesting metrics with colleagues
   - Discuss implementation strategies
   - Create team measurement standards

3. **Continuous Learning**:
   - Read metric descriptions thoroughly
   - Study practical examples
   - Apply learnings to your programs

### Advanced Usage

1. **API Integration**:
   - Use the API for custom applications
   - Integrate with existing systems
   - Automate data retrieval

2. **Custom Dashboards**:
   - Export data for external visualization
   - Create organization-specific views
   - Combine with other data sources

3. **Benchmarking**:
   - Compare with industry standards
   - Track improvement over time
   - Share best practices with peers

---

**Need additional help?** Contact our support team at support@ldmetrics.com or visit our [FAQ section](faq.md) for quick answers to common questions.
