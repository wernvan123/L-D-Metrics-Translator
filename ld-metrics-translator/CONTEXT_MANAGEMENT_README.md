# Context Management System

## Overview

The Context Management System is a comprehensive solution for managing user sessions, storing context data, and tracking metric selections in the L&D Metrics Translator application. It provides persistent user state management across sessions and enables personalized user experiences.

## Features

### Core Functionality
- **User Session Tracking**: Automatic session creation and management
- **Context Storage**: Flexible key-value context storage with expiration
- **Metric Selection Persistence**: Track and persist user metric selections
- **User Preferences**: Store and retrieve user preferences
- **Search History**: Maintain search context and history
- **API Integration**: RESTful API endpoints for all context operations

### Technical Features
- **Database Models**: Three new tables for comprehensive context management
- **Session Management**: Automatic session creation with unique identifiers
- **Data Validation**: Input validation and sanitization
- **Error Handling**: Comprehensive error handling and logging
- **Performance Optimization**: Database indexes for efficient queries
- **Cleanup Utilities**: Automatic cleanup of expired sessions and contexts

## Database Schema

### UserSession Table
```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_identifier VARCHAR(255),
    created_date DATETIME NOT NULL,
    last_activity DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    user_agent TEXT,
    ip_address VARCHAR(45)
);
```

### UserContext Table
```sql
CREATE TABLE user_contexts (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    context_type VARCHAR(50) NOT NULL,
    context_key VARCHAR(100) NOT NULL,
    context_data TEXT NOT NULL,
    created_date DATETIME NOT NULL,
    updated_date DATETIME NOT NULL,
    expires_at DATETIME,
    FOREIGN KEY (session_id) REFERENCES user_sessions(id),
    UNIQUE(session_id, context_type, context_key)
);
```

### MetricSelection Table
```sql
CREATE TABLE metric_selections (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    metric_id INTEGER NOT NULL,
    selection_type VARCHAR(50) DEFAULT 'manual',
    selected_at DATETIME NOT NULL,
    deselected_at DATETIME,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    context_tags TEXT,
    FOREIGN KEY (session_id) REFERENCES user_sessions(id),
    FOREIGN KEY (metric_id) REFERENCES metrics(id)
);
```

## API Endpoints

### Session Management
- `GET /api/context/session` - Get current session information
- `POST /api/context/initialize` - Initialize context for page load

### Context Storage
- `POST /api/context/store` - Store context data
- `GET /api/context/get/<type>/<key>` - Get specific context data
- `DELETE /api/context/delete/<type>/<key>` - Delete specific context
- `DELETE /api/context/clear` - Clear all contexts for session
- `GET /api/context/all` - Get all contexts for session

### User Preferences
- `GET /api/context/preferences` - Get user preferences
- `POST /api/context/preferences` - Update user preferences

### Metric Selection
- `POST /api/context/metrics/select` - Select/deselect a metric
- `GET /api/context/metrics/selected` - Get all selected metrics
- `DELETE /api/context/metrics/clear` - Clear all metric selections

### Search History
- `GET /api/context/search-history` - Get search history

## Usage Examples

### Backend (Python)

#### Using ContextManager Class
```python
from app.context_manager import context_manager

# Store context data
context_manager.store_context(
    context_type='search',
    context_key='last_query',
    context_data={'query': 'engagement', 'filters': {}}
)

# Retrieve context data
data = context_manager.get_context('search', 'last_query')

# Select a metric
selected, selection = context_manager.select_metric(metric_id=123)

# Get user preferences
prefs = context_manager.get_user_preferences()
```

#### Using Models Directly
```python
from app.models import UserSession, UserContext, MetricSelection

# Create or get session
session = UserSession.get_or_create('session_123', 'user_456')

# Store context
context = UserContext(
    session_id=session.id,
    context_type='preferences',
    context_key='theme',
    context_data='{"theme": "dark"}'
)
db.session.add(context)
db.session.commit()

# Toggle metric selection
selected, selection = MetricSelection.toggle_selection(
    session.id, metric_id=789
)
```

### Frontend (JavaScript)

#### Using Context Manager
```javascript
// Initialize context manager (automatic on page load)
await contextManager.init();

// Store context data
await contextManager.storeContext('search', 'last_query', {
    query: 'engagement metrics',
    filters: { outcome: 1 }
});

// Get context data
const data = await contextManager.getContext('search', 'last_query');

// Select a metric
const result = await contextManager.selectMetric(123, 'manual', ['performance']);

// Update preferences
await contextManager.updatePreferences({
    theme: 'dark',
    results_per_page: 25
});

// Get selected metrics
const selected = await contextManager.getSelectedMetrics();
```

#### Using API Directly
```javascript
// Store context via API
const response = await fetch('/api/context/store', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
    },
    body: JSON.stringify({
        context_type: 'search',
        context_key: 'last_query',
        context_data: { query: 'engagement' }
    })
});

// Select metric via API
const selectResponse = await fetch('/api/context/metrics/select', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
    },
    body: JSON.stringify({
        metric_id: 123,
        selection_type: 'manual'
    })
});
```

## Installation and Setup

### 1. Run Migration
```bash
python migrate_context_tables.py
```

### 2. Include JavaScript
Add to your HTML templates:
```html
<script src="/static/js/context-manager.js"></script>
```

### 3. Initialize on Page Load
```javascript
// Context manager initializes automatically
// Listen for initialization event
document.addEventListener('contextManager:contextInitialized', (event) => {
    console.log('Context Manager ready!');
});
```

## Configuration

### Context Manager Settings
```python
# In app/context_manager.py
class ContextManager:
    def __init__(self):
        self.default_context_expiry = timedelta(hours=24)  # Default expiration
        self.session_timeout = timedelta(hours=2)          # Session timeout
```

### Database Indexes
The system automatically creates these indexes for performance:
- `idx_user_contexts_session_type_key` - For context lookups
- `idx_metric_selections_session_active` - For active selections
- `idx_metric_selections_metric_id` - For metric-based queries

## Context Types

### Predefined Context Types
- **`search`** - Search queries and filters
- **`preferences`** - User preferences and settings
- **`selections`** - Current metric selections
- **`page`** - Page-specific context data

### Custom Context Types
You can create custom context types for specific use cases:
```python
# Store custom context
context_manager.store_context(
    context_type='custom_workflow',
    context_key='step_data',
    context_data={'current_step': 3, 'completed_steps': [1, 2]}
)
```

## Event System

### Frontend Events
The JavaScript Context Manager dispatches custom events:

```javascript
// Context initialized
document.addEventListener('contextManager:contextInitialized', (event) => {
    console.log('Session ID:', event.detail.sessionId);
});

// Metric selection changed
document.addEventListener('contextManager:metricSelectionChanged', (event) => {
    console.log('Metric', event.detail.action, ':', event.detail.metricId);
});

// Preferences updated
document.addEventListener('contextManager:preferencesUpdated', (event) => {
    console.log('New preferences:', event.detail.preferences);
});

// Selections cleared
document.addEventListener('contextManager:metricSelectionsCleared', (event) => {
    console.log('All selections cleared');
});
```

## Testing

### Run Tests
```bash
python -m pytest test_context_management.py -v
```

### Test Coverage
The test suite includes:
- Model validation and functionality
- Context Manager operations
- API endpoint testing
- Integration testing
- Error handling scenarios

### Demo Page
Visit `/context-demo` to test the Context Management System interactively.

## Performance Considerations

### Database Optimization
- Indexes on frequently queried columns
- Efficient join queries
- Automatic cleanup of expired data

### Memory Management
- JSON context data validation
- Configurable expiration times
- Session timeout handling

### Caching
- Local storage for preferences
- Session-based caching
- Efficient data retrieval

## Security Features

### Data Validation
- JSON schema validation
- Input sanitization
- SQL injection prevention

### Session Security
- Unique session identifiers
- IP address tracking
- User agent validation

### Access Control
- Session-based access
- Context isolation
- Secure data handling

## Monitoring and Logging

### Logging
All context operations are logged with appropriate levels:
```python
logger.info("Context stored: search:last_query")
logger.error("Failed to retrieve context: invalid JSON")
```

### Metrics
Track context system usage:
- Session creation rate
- Context storage operations
- Metric selection patterns
- Error rates

## Troubleshooting

### Common Issues

#### Session Not Found
```python
# Ensure session is created before use
session = context_manager.get_or_create_session()
```

#### Context Expiration
```python
# Check if context has expired
if context.is_expired():
    # Handle expired context
    context_manager.delete_context(context_type, context_key)
```

#### JavaScript Errors
```javascript
// Ensure context manager is initialized
if (window.contextManager && contextManager.initialized) {
    // Safe to use context manager
}
```

### Debug Mode
Enable debug logging:
```python
import logging
logging.getLogger('app.context_manager').setLevel(logging.DEBUG)
```

## Migration Notes

### From Previous Versions
If upgrading from a version without context management:
1. Run the migration script
2. Update templates to include context-manager.js
3. Initialize context on page load
4. Test functionality with demo page

### Database Backup
Always backup your database before running migrations:
```bash
cp app.db app.db.backup
```

## Future Enhancements

### Planned Features
- Redis backend for high-performance caching
- Advanced analytics on user behavior
- Context sharing between users
- Real-time context synchronization
- Advanced preference management

### Extensibility
The system is designed to be extensible:
- Custom context types
- Additional storage backends
- Enhanced security features
- Integration with external systems

## Support

### Documentation
- API documentation in code comments
- Comprehensive test suite
- Example implementations
- Demo page for testing

### Contributing
When contributing to the Context Management System:
1. Add tests for new functionality
2. Update documentation
3. Follow existing code patterns
4. Test with demo page

## License

This Context Management System is part of the L&D Metrics Translator project and follows the same licensing terms.
