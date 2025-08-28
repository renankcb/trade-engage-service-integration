# 🏗️ Architecture Documentation

## Overview

The TradeEngage Service Integration Service follows **Clean Architecture** principles with a clear separation of concerns, making it highly maintainable, testable, and extensible.

## 🏛️ Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  FastAPI Routes, Middleware, Dependencies, Schemas        │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                        │
│  Use Cases, Services, Interfaces, DTOs                    │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                           │
│  Entities, Value Objects, Events, Exceptions              │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                      │
│  Database, External APIs, Monitoring, Queue               │
├─────────────────────────────────────────────────────────────┤
│                   Background Layer                          │
│  Celery Workers, Scheduler, Task Management               │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. **API Layer** (`src/api/`)
- **Routes**: RESTful endpoints for job management
- **Middleware**: Error handling, logging, CORS, rate limiting
- **Dependencies**: Dependency injection for repositories and services
- **Schemas**: Pydantic models for request/response validation

### 2. **Application Layer** (`src/application/`)
- **Use Cases**: Business logic orchestration
  - `CreateJobRoutingUseCase`: Creates job routing and triggers sync
  - `SyncJobUseCase`: Synchronizes job with external provider
  - `PollUpdatesUseCase`: Polls providers for job status updates
  - `BatchSyncUseCase`: Processes multiple jobs in batch
- **Services**: Cross-cutting concerns
  - `ProviderManager`: Manages provider instances and rate limiting
  - `DataTransformer`: Transforms data between formats
  - `RateLimiter`: Controls API request rates
  - `RetryHandler`: Implements retry logic with exponential backoff
- **Interfaces**: Abstract contracts for dependencies

### 3. **Domain Layer** (`src/domain/`)
- **Entities**: Core business objects
  - `Job`: Represents a work order
  - `JobRouting`: Represents routing of job to a company
  - `Company`: Represents a business entity
  - `Technician`: Represents a worker
- **Value Objects**: Immutable business concepts
  - `SyncStatus`: Job synchronization status
  - `ProviderType`: Type of external provider
  - `Address`: Geographic location
- **Events**: Domain events for important business occurrences
- **Exceptions**: Domain-specific error types

### 4. **Infrastructure Layer** (`src/infrastructure/`)
- **Database**: PostgreSQL with SQLAlchemy async ORM
- **External APIs**: ServiceTitan, HousecallPro integrations
- **Monitoring**: Health checks, metrics, logging
- **Queue**: Redis-based job queue system

### 5. **Background Layer** (`src/background/`)
- **Celery**: Asynchronous task processing with Redis broker
- **Workers**: Specialized workers for different job types
  - `SyncWorker`: Processes job synchronization tasks
  - `PollWorker`: Handles status polling from providers
  - `CleanupWorker`: Manages data cleanup and archiving
- **Scheduler**: Periodic task execution with Celery Beat
- **Task Management**: Task queuing, retry logic, and monitoring

## 🔄 Data Flow

### Job Creation & Routing Flow
```
1. POST /api/jobs/
   ↓
2. CreateJobUseCase.execute()
   ↓
3. Validation (company, technician, address, homeowner)
   ↓
4. JobRepository.create() - Save job to database
   ↓
5. Find active companies with providers
   ↓
6. Create JobRouting for each company (excluding creating company)
   ↓
7. Return job with routings (status: pending)
   ↓
8. Background sync triggered automatically
```

### Background Synchronization Flow
```
1. Celery Beat Scheduler (every 5 minutes)
   ↓
2. sync_pending_jobs_task queued
   ↓
3. Celery Worker picks up task
   ↓
4. JobRoutingRepository.find_pending_sync()
   ↓
5. For each pending routing:
   ↓
6. SyncJobUseCase.execute()
   ↓
7. ProviderManager.get_provider(company.provider_type)
   ↓
8. Provider.create_lead(job_data)
   ↓
9. Update routing: status='synced', external_id=response.id
   ↓
10. Mark routing as successfully synced
```

### Status Polling Flow
```
1. Celery Beat Scheduler (every 30 minutes)
   ↓
2. poll_synced_jobs_task queued
   ↓
3. Celery Worker picks up task
   ↓
4. JobRoutingRepository.find_synced_for_polling()
   ↓
5. Group routings by provider/company for efficiency
   ↓
6. For each group:
   ↓
7. PollUpdatesUseCase.execute()
   ↓
8. Provider.get_job_status(batch of external_ids)
   ↓
9. Update job status, revenue, completion date
   ↓
10. Mark completed jobs as 'completed'
```

### Error Handling & Retry Flow
```
1. Sync/Poll operation fails
   ↓
2. Exception caught and logged
   ↓
3. RetryHandler.calculate_next_retry()
   ↓
4. Update routing: status='failed', error_message, next_retry_at
   ↓
5. Increment retry_count
   ↓
6. If retry_count < 3: Schedule retry
   ↓
7. If retry_count >= 3: Mark as permanently failed
   ↓
8. Admin can manually retry via API
```

### Polling Flow
```
1. Celery beat scheduler (every 30 minutes)
   ↓
2. poll_synced_jobs_task
   ↓
3. PollUpdatesUseCase.execute()
   ↓
4. Group jobs by provider/company
   ↓
5. Batch poll provider APIs
   ↓
6. Update job statuses
   ↓
7. Mark completed jobs
```

## 🏗️ Design Patterns

### 1. **Repository Pattern**
- Abstracts data access logic
- Enables easy testing and swapping implementations
- Provides clean interface for data operations

```python
class JobRoutingRepositoryInterface(ABC):
    async def get_by_id(self, id: UUID) -> Optional[JobRouting]
    async def save(self, job_routing: JobRouting) -> JobRouting
    async def find_pending_sync(self, limit: int) -> List[JobRouting]
```

### 2. **Factory Pattern**
- Creates provider instances based on type
- Encapsulates provider creation logic
- Enables easy addition of new providers

```python
class ProviderFactory:
    def create_provider(self, provider_type: ProviderType) -> ProviderInterface:
        if provider_type == ProviderType.SERVICETITAN:
            return ServiceTitanProvider()
        elif provider_type == ProviderType.HOUSECALLPRO:
            return HousecallProProvider()
        # ...
```

### 3. **Strategy Pattern**
- Different providers implement same interface
- Enables runtime provider selection
- Supports easy extension with new providers

### 4. **Observer Pattern**
- Domain events notify interested parties
- Enables loose coupling between components
- Supports audit trails and notifications

## 🔒 Security & Rate Limiting

### Rate Limiting Strategy
- **Sliding Window**: More accurate than fixed windows
- **Provider-Specific**: Different limits for different APIs
- **Automatic Throttling**: Queues requests when limits exceeded
- **Fail-Open**: Continues operation if rate limiting fails

### Configuration
```python
DEFAULT_RATE_LIMITS = {
    "servicetitan": RateLimitConfig(
        requests_per_minute=60,  # 1 request per second
        requests_per_hour=3600,
        burst_limit=10
    ),
    "housecallpro": RateLimitConfig(
        requests_per_minute=120,  # 2 requests per second
        requests_per_hour=7200,
        burst_limit=20
    )
}
```

## 📊 Monitoring & Observability

### Health Checks
- **Database**: Connection and query performance
- **Redis**: Connection and operations
- **Celery**: Worker status and broker
- **Providers**: Factory and validation
- **System**: Resource usage

### Metrics
- **Business Metrics**: Job sync counts, durations, success rates
- **Infrastructure Metrics**: Database connections, queue depths
- **Provider Metrics**: API calls, errors, rate limits

### Logging
- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: Appropriate verbosity for each environment
- **Context**: Request IDs, user context, business context

## ⚙️ Workers & Schedulers

### Celery Architecture

The system uses Celery for distributed task processing with the following components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Celery Beat   │    │   Redis Broker  │    │  Celery Workers │
│   (Scheduler)   │───▶│   (Message      │───▶│  (Task          │
│                 │    │    Queue)       │    │   Processors)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Scheduled Tasks

#### 1. **Job Synchronization Task** (`sync_pending_jobs_task`)
- **Frequency**: Every 5 minutes
- **Purpose**: Process pending job routings and sync with external providers
- **Implementation**: `src/background/tasks/sync_jobs.py`
- **Process**:
  ```python
  @celery_app.task
  async def sync_pending_jobs_task():
      # Find pending routings
      pending_routings = await job_routing_repo.find_pending_sync(limit=50)
      
      # Process each routing
      for routing in pending_routings:
          await sync_job_use_case.execute(routing)
  ```

#### 2. **Status Polling Task** (`poll_synced_jobs_task`)
- **Frequency**: Every 30 minutes
- **Purpose**: Fetch job updates from external providers
- **Implementation**: `src/background/tasks/sync_jobs.py`
- **Process**:
  ```python
  @celery_app.task
  async def poll_synced_jobs_task():
      # Find synced routings ready for polling
      synced_routings = await job_routing_repo.find_synced_for_polling(limit=100)
      
      # Group by provider/company for efficiency
      grouped_routings = group_by_provider(synced_routings)
      
      # Poll each provider
      for provider_type, routings in grouped_routings.items():
          await poll_updates_use_case.execute(provider_type, routings)
  ```

#### 3. **Retry Failed Jobs Task** (`retry_failed_jobs_task`)
- **Frequency**: Every 15 minutes
- **Purpose**: Retry failed synchronizations with exponential backoff
- **Implementation**: `src/background/tasks/sync_jobs.py`
- **Process**:
  ```python
  @celery_app.task
  async def retry_failed_jobs_task():
      # Find failed routings ready for retry
      failed_routings = await job_routing_repo.find_failed_for_retry(limit=25)
      
      # Retry each routing
      for routing in failed_routings:
          if routing.should_retry():
              await sync_job_use_case.execute(routing)
  ```

#### 4. **Cleanup Old Jobs Task** (`cleanup_old_jobs_task`)
- **Frequency**: Daily at 2:00 AM
- **Purpose**: Archive completed jobs and maintain database performance
- **Implementation**: `src/background/tasks/cleanup_jobs.py`
- **Process**:
  ```python
  @celery_app.task
  async def cleanup_old_jobs_task():
      # Find old completed jobs (older than 90 days)
      old_jobs = await job_repo.find_old_completed_jobs(days=90)
      
      # Archive to separate table
      await archive_jobs(old_jobs)
      
      # Remove from main tables
      await job_repo.delete_old_jobs(days=90)
  ```

### Worker Types

#### **Sync Worker** (`src/background/workers/sync_worker.py`)
- **Purpose**: Process job synchronization tasks
- **Responsibilities**:
  - Execute `sync_pending_jobs_task`
  - Handle ServiceTitan API calls
  - Manage retry logic and error handling
  - Update routing status and external IDs
- **Configuration**:
  ```python
  class SyncWorker:
      def __init__(self, provider_manager, job_routing_repo):
          self.provider_manager = provider_manager
          self.job_routing_repo = job_routing_repo
      
      async def sync_jobs(self, routings):
          for routing in routings:
              try:
                  await self._sync_single_job(routing)
              except Exception as e:
                  await self._handle_sync_error(routing, e)
  ```

#### **Poll Worker** (`src/background/workers/poll_worker.py`)
- **Purpose**: Handle status polling from external providers
- **Responsibilities**:
  - Execute `poll_synced_jobs_task`
  - Batch API calls for efficiency
  - Update job status and revenue
  - Record metrics and performance data
- **Configuration**:
  ```python
  class PollWorker:
      def __init__(self, provider_manager, job_repo):
          self.provider_manager = provider_manager
          self.job_repo = job_repo
      
      async def poll_updates(self, provider_type, routings):
          # Group routings by company for batch processing
          grouped = self._group_by_company(routings)
          
          for company_id, company_routings in grouped.items():
              await self._poll_company_updates(company_id, company_routings)
  ```

#### **Cleanup Worker** (`src/background/workers/cleanup_worker.py`)
- **Purpose**: Manage data cleanup and archiving
- **Responsibilities**:
  - Execute `cleanup_old_jobs_task`
  - Archive historical data
  - Maintain database performance
  - Clean up temporary files and logs
- **Configuration**:
  ```python
  class CleanupWorker:
      def __init__(self, job_repo, archive_repo):
          self.job_repo = job_repo
          self.archive_repo = archive_repo
      
      async def cleanup_old_jobs(self, days_old=90):
          old_jobs = await self.job_repo.find_old_completed_jobs(days_old)
          await self.archive_repo.archive_jobs(old_jobs)
          await self.job_repo.delete_old_jobs(days_old)
  ```

### Task Queue Management

#### **Redis Broker Configuration**
```python
# Celery configuration
CELERY_CONFIG = {
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'UTC',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 30 * 60,  # 30 minutes
    'task_soft_time_limit': 25 * 60,  # 25 minutes
}
```

#### **Queue Structure**
```
Redis Queues:
├── default          # General tasks
├── sync_jobs       # Job synchronization tasks
├── poll_updates    # Status polling tasks
├── retry_failed    # Retry failed jobs
└── cleanup         # Data cleanup tasks
```

#### **Task Priority System**
1. **High Priority**: Retry failed jobs, manual sync requests
2. **Medium Priority**: Regular job synchronization
3. **Low Priority**: Status polling, cleanup tasks

### Monitoring & Health Checks

#### **Worker Health Monitoring**
```python
# Health check endpoint
@app.get("/api/health/component/celery")
async def check_celery_health():
    try:
        # Check worker status
        worker_stats = celery_app.control.inspect().stats()
        
        # Check queue depths
        queue_depths = celery_app.control.inspect().active_queues()
        
        return {
            "status": "healthy",
            "workers": len(worker_stats),
            "queues": queue_depths,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }
```

#### **Task Metrics**
- **Success Rate**: Percentage of successful task executions
- **Processing Time**: Average time to complete tasks
- **Queue Depth**: Number of pending tasks in each queue
- **Worker Utilization**: CPU and memory usage per worker
- **Error Rates**: Frequency and types of task failures

#### **Alerting**
- **Worker Down**: Alert when workers stop responding
- **High Queue Depth**: Alert when queues exceed thresholds
- **High Error Rate**: Alert when task failure rate increases
- **Long Processing Times**: Alert when tasks take too long

## 🚀 Performance & Scaling

### Database Optimization
- **Connection Pooling**: Efficient database connections
- **Async Queries**: Non-blocking database operations
- **Indexing**: Optimized queries for common patterns
- **Batch Operations**: Process multiple records efficiently

### Caching Strategy
- **Redis**: Session data, rate limiting, job queues
- **In-Memory**: Provider instances, configuration
- **Database**: Frequently accessed business data

### Async Processing
- **Celery Workers**: Parallel job processing
- **Async/Await**: Non-blocking I/O operations
- **Background Tasks**: Offload time-consuming operations

## 🔧 Configuration Management

### Environment-Based
- **Development**: Debug mode, verbose logging
- **Staging**: Production-like with test data
- **Production**: Optimized, minimal logging

### Provider Configuration
```python
provider_config = {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "tenant_id": "your_tenant_id",
    "base_url": "https://api.servicetitan.io",
    "timeout": 30,
    "retry_attempts": 3
}
```

## 🧪 Testing Strategy

### Test Pyramid
```
        E2E Tests (Few)
           ▲
    Integration Tests (Some)
           ▲
      Unit Tests (Many)
```

### Test Types
- **Unit Tests**: Individual components in isolation
- **Integration Tests**: Component interactions
- **E2E Tests**: Complete user workflows
- **Performance Tests**: Load and stress testing

### Test Data
- **Fixtures**: Reusable test data
- **Factories**: Dynamic test data generation
- **Mocks**: External service simulation

## 🚀 Deployment & DevOps

### Containerization
- **Docker**: Application containerization
- **Docker Compose**: Local development environment
- **Multi-stage Builds**: Optimized production images

### Environment Management
- **Environment Variables**: Configuration injection
- **Secrets Management**: Secure credential handling
- **Configuration Validation**: Runtime configuration checks

### Monitoring & Alerting
- **Health Checks**: Service availability monitoring
- **Metrics Collection**: Performance and business metrics
- **Log Aggregation**: Centralized logging
- **Alerting**: Proactive issue notification

## 🔮 Future Enhancements

### Planned Features
- **Webhook Support**: Real-time updates from providers
- **Advanced Retry Strategies**: Circuit breaker patterns
- **Multi-Region Support**: Geographic distribution
- **Advanced Analytics**: Business intelligence dashboards

### Scalability Improvements
- **Microservices**: Service decomposition
- **Event Sourcing**: Complete audit trail
- **CQRS**: Separate read/write models
- **API Gateway**: Centralized API management

## 📚 Best Practices

### Code Quality
- **Type Hints**: Full type annotation
- **Documentation**: Comprehensive docstrings
- **Error Handling**: Graceful error management
- **Logging**: Appropriate log levels and context

### Performance
- **Async Operations**: Non-blocking I/O
- **Connection Pooling**: Efficient resource usage
- **Caching**: Reduce redundant operations
- **Batch Processing**: Process multiple items efficiently

### Security
- **Input Validation**: Comprehensive data validation
- **Rate Limiting**: Prevent API abuse
- **Error Handling**: Don't expose sensitive information
- **Audit Logging**: Track all operations

---

This architecture provides a solid foundation for a production-ready integration service that can scale with business needs while maintaining code quality and operational excellence.
