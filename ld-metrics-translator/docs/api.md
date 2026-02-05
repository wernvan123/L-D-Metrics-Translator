# API Documentation

The L&D Metrics Translator provides a comprehensive RESTful API for accessing and managing learning metrics data.

## Base URL

```
http://localhost:5000/api  # Development
https://your-domain.com/api  # Production
```

## Authentication

Currently, the API is publicly accessible for read operations. Admin operations require authentication through the web interface.

## Rate Limiting

- **General endpoints**: 100 requests per hour per IP
- **Search endpoints**: 50 requests per hour per IP
- **Admin endpoints**: 20 requests per hour per IP

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Response Format

All API responses follow a consistent JSON format:

### Success Response
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional error details"
  }
}
```

> Note: Some endpoints (notably Event Analysis) return a different payload shape (e.g., `{ "success": true, ... }`) because they are optimized for UI workflows and asynchronous execution.

## Endpoints

### Health Check

Check the health and status of the API.

**GET** `/api/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1705312200.123,
  "version": "1.0.0",
  "database": "healthy",
  "uptime": 86400.5
}
```

**Status Codes:**
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service is unhealthy

---

### Diagnostics: Event Analysis (Async)

The application includes an asynchronous Event Analysis workflow used by the Diagnostics UI (`/diagnostics`).

#### Submit Event Analysis Job

**POST** `/api/analyze-event`

**Request body:**
```json
{
  "event_description": "Team struggled with deadline due to unclear ownership",
  "selected_metrics": [],
  "role_profile_id": 1,
  "kb_context": "Optional context string",
  "kb_tier_limit": 5,
  "kb_related_limit": 10
}
```

Notes:
- `event_description` is required.
- `role_profile_id` is optional. When supplied, the analysis can incorporate role context.
- The endpoint returns a `202` with a `job_id` that must be polled for completion.

**Example response (202):**
```json
{
  "success": true,
  "job_id": "<job_id>",
  "status": "queued",
  "timestamp": 1730000000.123
}
```

#### Poll Job Status / Retrieve Result

**GET** `/api/analyze-event/<job_id>`

**Example response (running/queued):**
```json
{
  "success": true,
  "status": "running",
  "job_id": "<job_id>",
  "created_at": "2026-01-01T12:00:00Z",
  "started_at": "2026-01-01T12:00:02Z",
  "timestamp": 1730000002.456
}
```

**Example response (succeeded):**
```json
{
  "success": true,
  "analysis": "...",
  "generated_by": "ai",
  "ollama_status": "available",
  "timestamp": 1730000010.789,
  "kb": {
    "strong": [],
    "related": [],
    "biases": []
  },
  "analysis_id": 123
}
```

**Example response (failed):**
```json
{
  "success": false,
  "status": "failed",
  "error": "Analysis failed",
  "timestamp": 1730000010.789
}
```

---

### Metrics

#### Get All Metrics

Retrieve all metrics with optional filtering and pagination.

**GET** `/api/metrics`

**Query Parameters:**
- `outcome` (integer, optional): Filter by L&D outcome ID
- `type` (integer, optional): Filter by metric type ID
- `q` (string, optional): Search term for name, description, example
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Items per page (default: 20, max: 100)

**Example Request:**
```bash
GET /api/metrics?outcome=1&type=2&page=1&per_page=10
```

**Example Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Employee Engagement Score",
      "description": "Measures overall employee satisfaction and commitment",
      "example": "Annual engagement survey showing 85% positive responses",
      "ld_outcome": {
        "id": 1,
        "name": "Engagement",
        "description": "Learning initiatives that boost employee engagement"
      },
      "metric_type": {
        "id": 2,
        "name": "Behavioral Metric",
        "description": "Metrics that measure observable behaviors"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 45,
    "pages": 5
  }
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

#### Search Metrics

Perform full-text search across metrics.

**GET** `/api/metrics/search`

**Query Parameters:**
- `q` (string, required): Search term
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Items per page (default: 20, max: 100)

**Example Request:**
```bash
GET /api/metrics/search?q=engagement&page=1&per_page=5
```

**Example Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Employee Engagement Score",
      "description": "Measures overall employee satisfaction and commitment",
      "example": "Annual engagement survey showing 85% positive responses",
      "ld_outcome": {
        "id": 1,
        "name": "Engagement"
      },
      "metric_type": {
        "id": 2,
        "name": "Behavioral Metric"
      },
      "relevance_score": 0.95
    }
  ],
  "search_meta": {
    "query": "engagement",
    "total_results": 12,
    "search_time_ms": 45
  }
}
```

---

### L&D Outcomes

#### Get All L&D Outcomes

Retrieve all available L&D outcomes.

**GET** `/api/outcomes`

**Example Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Engagement",
      "description": "Learning initiatives that boost employee engagement and satisfaction",
      "metrics_count": 15
    },
    {
      "id": 2,
      "name": "Retention",
      "description": "Learning programs that improve employee retention rates",
      "metrics_count": 12
    }
  ]
}
```

---

### Metric Types

#### Get All Metric Types

Retrieve all available metric types.

**GET** `/api/types`

**Example Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Operational KPI",
      "description": "Key performance indicators that measure operational efficiency",
      "metrics_count": 25
    },
    {
      "id": 2,
      "name": "Behavioral Metric",
      "description": "Metrics that measure observable behaviors and actions",
      "metrics_count": 18
    }
  ]
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_PARAMETER` | One or more request parameters are invalid |
| `RESOURCE_NOT_FOUND` | Requested resource does not exist |
| `RATE_LIMIT_EXCEEDED` | API rate limit has been exceeded |
| `SEARCH_QUERY_REQUIRED` | Search query parameter is required |
| `PAGINATION_ERROR` | Invalid pagination parameters |
| `DATABASE_ERROR` | Database connection or query error |
| `INTERNAL_ERROR` | Unexpected server error |

## Usage Examples

### Python

```python
import requests

# Get all metrics
response = requests.get('http://localhost:5000/api/metrics')
metrics = response.json()['data']

# Search for engagement metrics
response = requests.get(
    'http://localhost:5000/api/metrics/search',
    params={'q': 'engagement', 'per_page': 10}
)
results = response.json()['data']

# Filter by outcome and type
response = requests.get(
    'http://localhost:5000/api/metrics',
    params={'outcome': 1, 'type': 2}
)
filtered_metrics = response.json()['data']
```

### JavaScript

```javascript
// Fetch all metrics
fetch('/api/metrics')
  .then(response => response.json())
  .then(data => {
    console.log('Metrics:', data.data);
  });

// Search metrics
fetch('/api/metrics/search?q=performance')
  .then(response => response.json())
  .then(data => {
    console.log('Search results:', data.data);
  });

// Get outcomes
fetch('/api/outcomes')
  .then(response => response.json())
  .then(data => {
    console.log('Outcomes:', data.data);
  });
```

### cURL

```bash
# Get all metrics
curl -X GET "http://localhost:5000/api/metrics"

# Search metrics
curl -X GET "http://localhost:5000/api/metrics/search?q=engagement"

# Get metrics with filters
curl -X GET "http://localhost:5000/api/metrics?outcome=1&type=2&page=1&per_page=10"

# Health check
curl -X GET "http://localhost:5000/api/health"
```

## Webhooks (Future Feature)

Planned webhook support for real-time notifications:
- New metric additions
- Metric updates
- Search analytics
- System health alerts

## SDK Support (Future Feature)

Official SDKs planned for:
- Python
- JavaScript/Node.js
- PHP
- C#

## Changelog

### v1.0.0 (Current)
- Initial API release
- Basic CRUD operations for metrics
- Search functionality
- Health check endpoint
- Rate limiting

### Planned Features
- Authentication and authorization
- Metric creation/update via API
- Advanced analytics endpoints
- Webhook support
- GraphQL endpoint
- OpenAPI/Swagger documentation
