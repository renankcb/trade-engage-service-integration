# TradeEngage Service Integration API

## Overview

The TradeEngage Service Integration API provides a comprehensive interface for managing job routing and synchronization with external Point of Sale (PoS) providers like ServiceTitan.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API operates without authentication for development purposes. In production, implement proper authentication mechanisms.

## Endpoints

### Jobs

#### Create Job with Intelligent Matching

Creates a new job and automatically routes it to suitable companies based on skills and requirements.

**Endpoint:** `POST /jobs/`

**Request Body:**
```json
{
  "summary": "Kitchen faucet replacement needed urgently",
  "address": {
    "street": "123 Main Street",
    "city": "Anytown",
    "state": "CA",
    "zip_code": "90210"
  },
  "homeowner": {
    "name": "John Doe",
    "phone": "(555) 123-4567",
    "email": "john.doe@email.com"
  },
  "created_by_company_id": "uuid-of-requesting-company",
  "created_by_technician_id": "uuid-of-identifying-technician",
  "required_skills": ["plumbing", "electrical"],
  "skill_levels": {
    "plumbing": "expert",
    "electrical": "intermediate"
  },
  "category": "plumbing"
}
```

**Field Descriptions:**
- `summary`: Description of the job/work needed
- `address`: Service location details
- `homeowner`: Customer contact information
- `created_by_company_id`: Company that REQUESTED the job
- `created_by_technician_id`: Technician that IDENTIFIED the need
- `required_skills`: List of skills needed for this job
- `skill_levels`: Required skill level for each skill (basic, intermediate, expert)
- `category`: Job category for classification (plumbing, HVAC, electrical, general)

**Response (201 Created):**
```json
{
  "id": "job-uuid-here",
  "summary": "Kitchen faucet replacement needed urgently",
  "address": {
    "street": "123 Main Street",
    "city": "Anytown",
    "state": "CA",
    "zip_code": "90210"
  },
  "homeowner": {
    "name": "John Doe",
    "phone": "(555) 123-4567",
    "email": "john.doe@email.com"
  },
  "created_by_company_id": "uuid-of-requesting-company",
  "created_by_technician_id": "uuid-of-identifying-technician",
  "status": "pending",
  "revenue": null,
  "completed_at": null,
  "created_at": "2025-08-27T16:00:00Z",
  "updated_at": "2025-08-27T16:00:00Z"
}
```

**Business Logic:**
1. **Validation**: Ensures requesting company and technician exist and are related
2. **Intelligent Matching**: Uses skills and category to find suitable companies
3. **Atomic Creation**: Job, routings, and outbox events are created in a single transaction
4. **Automatic Routing**: Creates routings for matched companies (excluding requesting company)
5. **Outbox Events**: Generates events for immediate synchronization

#### Get Job Details

Retrieves detailed information about a specific job.

**Endpoint:** `GET /jobs/{job_id}`

**Response (200 OK):**
```json
{
  "id": "job-uuid-here",
  "summary": "Kitchen faucet replacement needed urgently",
  "address": {
    "street": "123 Main Street",
    "city": "Anytown",
    "state": "CA",
    "zip_code": "90210"
  },
  "homeowner": {
    "name": "John Doe",
    "phone": "(555) 123-4567",
    "email": "john.doe@email.com"
  },
  "created_by_company_id": "uuid-of-requesting-company",
  "created_by_technician_id": "uuid-of-identifying-technician",
  "status": "pending",
  "revenue": null,
  "completed_at": null,
  "created_at": "2025-08-27T16:00:00Z",
  "updated_at": "2025-08-27T16:00:00Z"
}
```

#### List All Jobs

Retrieves a paginated list of all jobs.

**Endpoint:** `GET /jobs/?skip=0&limit=100`

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)

**Response (200 OK):**
```json
[
  {
    "id": "job-uuid-1",
    "summary": "Kitchen faucet replacement needed urgently",
    "address": {...},
    "homeowner": {...},
    "created_by_company_id": "uuid-1",
    "created_by_technician_id": "uuid-1",
    "status": "pending",
    "revenue": null,
    "completed_at": null,
    "created_at": "2025-08-27T16:00:00Z",
    "updated_at": "2025-08-27T16:00:00Z"
  },
  {
    "id": "job-uuid-2",
    "summary": "HVAC system maintenance and inspection",
    "address": {...},
    "homeowner": {...},
    "created_by_company_id": "uuid-2",
    "created_by_technician_id": "uuid-2",
    "status": "completed",
    "revenue": 450.00,
    "completed_at": "2025-08-27T18:00:00Z",
    "created_at": "2025-08-27T16:00:00Z",
    "updated_at": "2025-08-27T18:00:00Z"
  }
]
```

### Job Routings

#### Get Job Routings

Retrieves all routings for a specific job.

**Endpoint:** `GET /jobs/{job_id}/routings`

**Response (200 OK):**
```json
[
  {
    "id": "routing-uuid-1",
    "job_id": "job-uuid-here",
    "company_id_received": "company-uuid-1",
    "external_id": "st-12345",
    "sync_status": "synced",
    "retry_count": 0,
    "last_sync_attempt": "2025-08-27T16:01:00Z",
    "last_synced_at": "2025-08-27T16:01:00Z",
    "error_message": null,
    "created_at": "2025-08-27T16:00:00Z",
    "updated_at": "2025-08-27T16:01:00Z"
  },
  {
    "id": "routing-uuid-2",
    "job_id": "job-uuid-here",
    "company_id_received": "company-uuid-2",
    "external_id": null,
    "sync_status": "pending",
    "retry_count": 0,
    "last_sync_attempt": null,
    "last_synced_at": null,
    "error_message": null,
    "created_at": "2025-08-27T16:00:00Z",
    "updated_at": "2025-08-27T16:00:00Z"
  }
]
```

#### Sync Job to Company

Manually triggers synchronization of a job routing to a specific company.

**Endpoint:** `POST /jobs/{job_id}/sync`

**Request Body:**
```json
{
  "company_id": "company-uuid-here"
}
```

**Response (200 OK):**
```json
{
  "id": "routing-uuid-here",
  "job_id": "job-uuid-here",
  "company_id_received": "company-uuid-here",
  "external_id": "st-12345",
  "sync_status": "synced",
  "retry_count": 0,
  "last_sync_attempt": "2025-08-27T16:01:00Z",
  "last_synced_at": "2025-08-27T16:01:00Z",
  "error_message": null,
  "created_at": "2025-08-27T16:00:00Z",
  "updated_at": "2025-08-27T16:01:00Z"
}
```

### Health Checks

#### Basic Health Check

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-27T16:00:00Z",
  "version": "1.0.0"
}
```

#### Detailed Health Check

**Endpoint:** `GET /health/detailed`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-27T16:00:00Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": "15ms"
    },
    "redis": {
      "status": "healthy",
      "response_time": "2ms"
    },
    "external_apis": {
      "status": "healthy",
      "providers": {
        "servicetitan": "healthy",
        "mock": "healthy"
      }
    }
  }
}
```

#### Readiness Probe

**Endpoint:** `GET /health/ready`

**Response (200 OK):**
```json
{
  "status": "ready",
  "timestamp": "2025-08-27T16:00:00Z"
}
```

#### Liveness Probe

**Endpoint:** `GET /health/live`

**Response (200 OK):**
```json
{
  "status": "alive",
  "timestamp": "2025-08-27T16:00:00Z"
}
```

## Data Models

### Address Schema

```json
{
  "street": "string (required, max 255 chars)",
  "city": "string (required, max 100 chars)",
  "state": "string (required, exactly 2 chars, uppercase)",
  "zip_code": "string (required, 5-10 chars)"
}
```

### Homeowner Schema

```json
{
  "name": "string (required, max 255 chars)",
  "phone": "string (optional, max 20 chars)",
  "email": "string (optional, max 255 chars, email format)"
}
```

### Job Schema

```json
{
  "id": "UUID (auto-generated)",
  "summary": "string (required, max 1000 chars)",
  "address": "Address object (required)",
  "homeowner": "Homeowner object (required)",
  "created_by_company_id": "UUID (required)",
  "created_by_technician_id": "UUID (required)",
  "required_skills": "array of strings (optional)",
  "skill_levels": "object (optional, skill_name -> level mapping)",
  "category": "string (optional, max 100 chars)",
  "status": "string (default: 'pending')",
  "revenue": "decimal (optional, 2 decimal places)",
  "completed_at": "datetime (optional)",
  "created_at": "datetime (auto-generated)",
  "updated_at": "datetime (auto-updated)"
}
```

### Job Routing Schema

```json
{
  "id": "UUID (auto-generated)",
  "job_id": "UUID (required)",
  "company_id_received": "UUID (required)",
  "external_id": "string (optional, max 255 chars)",
  "sync_status": "enum (pending, processing, synced, failed, completed)",
  "retry_count": "integer (default: 0)",
  "last_sync_attempt": "datetime (optional)",
  "last_synced_at": "datetime (optional)",
  "error_message": "string (optional)",
  "claimed_at": "datetime (optional)",
  "created_at": "datetime (auto-generated)",
  "updated_at": "datetime (auto-updated)"
}
```

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message description",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-08-27T16:00:00Z"
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Input validation failed
- `NOT_FOUND`: Requested resource not found
- `SYNC_ERROR`: External provider synchronization failed
- `INTERNAL_ERROR`: Unexpected internal error

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input or validation error
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Unexpected server error

## Rate Limiting

The API implements rate limiting to protect against abuse:

- **Default**: 100 requests per minute per IP
- **Job Creation**: 10 requests per minute per IP
- **Health Checks**: No rate limiting

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Monitoring & Metrics

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint:

- `job_creation_total`: Total jobs created
- `job_routing_total`: Total job routings created
- `sync_success_total`: Successful synchronizations
- `sync_failure_total`: Failed synchronizations
- `api_request_duration_seconds`: API response times
- `queue_depth`: Background task queue depths

### Structured Logging

All API requests are logged with structured data:

```json
{
  "level": "INFO",
  "message": "Job created successfully",
  "method": "POST",
  "path": "/api/v1/jobs/",
  "status_code": 201,
  "response_time_ms": 245,
  "job_id": "uuid-here",
  "matching_score": 4.5,
  "correlation_id": "req-123"
}
```

## Background Processing

### Outbox Events

The API creates outbox events for reliable background processing:

```json
{
  "event_type": "job_sync",
  "aggregate_id": "routing-uuid",
  "event_data": {
    "routing_id": "routing-uuid",
    "job_id": "job-uuid",
    "company_id": "company-uuid",
    "matching_score": 4.5,
    "matched_skills": ["plumbing"],
    "provider_type": "servicetitan"
  }
}
```

### Processing Guarantees

- **Immediate Processing**: Outbox events are processed within 30 seconds
- **SLA Compliance**: Job synchronization guaranteed within 5 minutes
- **Retry Logic**: Automatic retry with exponential backoff
- **Dead Letter Queue**: Failed events are preserved for manual review

## Examples

### Complete Job Creation Flow

```bash
# 1. Create a job with plumbing skills
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Fix leaky kitchen faucet",
    "address": {
      "street": "456 Oak Avenue",
      "city": "Springfield",
      "state": "IL",
      "zip_code": "62701"
    },
    "homeowner": {
      "name": "Jane Smith",
      "phone": "(555) 987-6543",
      "email": "jane.smith@email.com"
    },
    "created_by_company_id": "company-uuid-here",
    "created_by_technician_id": "technician-uuid-here",
    "required_skills": ["plumbing"],
    "skill_levels": {"plumbing": "expert"},
    "category": "plumbing"
  }'

# 2. Check job routings
curl "http://localhost:8000/api/v1/jobs/{job-id}/routings"

# 3. Monitor sync status
curl "http://localhost:8000/api/v1/jobs/{job-id}/routings"
```

### Health Monitoring

```bash
# Check overall health
curl "http://localhost:8000/api/v1/health"

# Detailed component health
curl "http://localhost:8000/api/v1/health/detailed"

# Kubernetes readiness probe
curl "http://localhost:8000/api/v1/health/ready"

# Kubernetes liveness probe
curl "http://localhost:8000/api/v1/health/live"
```

## Development

### Local Development

```bash
# Start development environment
make dev

# Run tests
make test

# Check code quality
make lint

# Format code
make format
```

### API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

## Support

For API support or questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the architecture documentation
