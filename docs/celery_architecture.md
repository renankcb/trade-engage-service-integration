# Celery Architecture - Service Integration

## Overview

This document describes the architecture and implementation of the Celery-based background job processing system in the Service Integration project.

## Architecture Components

### 1. Immediate Execution (OutboxWorker)
- **Purpose**: Primary path for job synchronization
- **Frequency**: Every 30 seconds
- **Function**: Processes JOB_SYNC events immediately
- **Implementation**: `src/background/workers/outbox_worker.py`

#### Key Features:
- **Duplicate Prevention**: Tracks queued routings to prevent duplicate task execution
- **Event Processing**: Processes outbox events in batches
- **Error Handling**: Comprehensive error handling and retry logic
- **Memory Management**: Automatic cleanup of tracking data

#### Flow:
```
1. OutboxWorker starts (every 30s)
2. Retrieves pending outbox events
3. For each JOB_SYNC event:
   - Checks if routing already queued
   - If not: enqueues sync_job_task.delay()
   - Marks routing as queued to prevent duplicates
4. Processes events and updates status
```

### 2. Backup Execution (Celery Beat)
- **Purpose**: Safety net for jobs missed by OutboxWorker
- **Frequency**: Every 2 minutes
- **Function**: Processes "stuck" job routings
- **Implementation**: `src/background/tasks/sync_jobs.py`

#### Key Features:
- **Stuck Detection**: Only processes routings older than 5 minutes
- **Duplicate Prevention**: Prevents duplicates within the same batch
- **Status Tracking**: Marks routings as "processing" to prevent interference
- **Efficient Processing**: Smaller batch size (20 vs 50) for backup operations

#### Flow:
```
1. Celery Beat triggers sync_pending_jobs_task (every 2 min)
2. Finds routings that are "stuck" (>5 min old)
3. For each stuck routing:
   - Checks for duplicates in current batch
   - Marks as "processing" to prevent interference
   - Enqueues sync_job_task.delay()
4. Commits all changes atomically
```

### 3. Individual Task Execution
- **Purpose**: Processes individual job routings
- **Trigger**: Called by both OutboxWorker and backup task
- **Function**: Handles actual sync operation with external providers
- **Implementation**: `src/application/use_cases/sync_job.py`

#### Key Features:
- **Race Condition Prevention**: Double validation of status before execution
- **Idempotency**: Handles duplicate execution gracefully
- **Status Management**: Marks routing as "processing" during execution
- **Comprehensive Error Handling**: Detailed logging and error recovery

#### Flow:
```
1. Task receives routing_id
2. Loads and validates job routing
3. Double-checks status to prevent race conditions
4. Marks as "processing" to prevent interference
5. Executes sync operation with provider
6. Updates status based on result
7. Commits transaction
```

## Data Flow

### Job Creation Flow:
```
API Request → Create Job → Create JobRouting → Create OutboxEvent → OutboxWorker → Celery Task → Provider Sync
```

### Backup Flow:
```
Celery Beat → Find Stuck Routings → Enqueue Tasks → Individual Processing → Status Update
```

### Polling Flow:
```
Celery Beat → Poll Synced Jobs → Check Provider Status → Update Job Status → Mark Completed
```

## Configuration

### Environment Variables:
```bash
# Background Workers
BACKGROUND_WORKER_OUTBOX_INTERVAL_SECONDS=30
BACKGROUND_WORKER_POLL_INTERVAL_SECONDS=60

# Celery Beat Scheduler
CELERY_SYNC_PENDING_JOBS_INTERVAL_SECONDS=120  # 2 minutes
CELERY_POLL_JOB_UPDATES_INTERVAL_SECONDS=20     # 20 seconds
CELERY_RETRY_FAILED_JOBS_INTERVAL_SECONDS=600   # 10 minutes
```

### Celery Configuration:
```python
# Worker Configuration
worker_concurrency=4                    # 4 worker processes
worker_max_tasks_per_child=100         # Restart after 100 tasks
worker_max_memory_per_child=200000     # 200MB memory limit

# Task Configuration
task_soft_time_limit=480               # 8 minutes soft timeout
task_time_limit=600                    # 10 minutes hard timeout
```

## Error Handling

### Duplicate Prevention:
- **OutboxWorker**: Tracks queued routings in memory
- **Backup Task**: Prevents duplicates within batch
- **Individual Tasks**: Status validation and marking

### Race Condition Prevention:
- **Double Validation**: Check status before and after loading
- **Status Marking**: Mark as "processing" during execution
- **Transaction Isolation**: Use database transactions for consistency

### Retry Logic:
- **Exponential Backoff**: 5, 10, 20 minutes between retries
- **Max Retries**: 3 attempts before marking as permanently failed
- **Status Tracking**: Track retry count and next retry time

## Monitoring and Observability

### Logging:
- **Structured Logging**: Consistent log format across all components
- **Context Information**: Include routing_id, company_id, provider_type
- **Performance Metrics**: Track processing time and success rates

### Metrics:
- **Task Counters**: Total processed, errors, success rate
- **Performance Metrics**: Processing time, queue depth
- **Health Checks**: Worker status, queue health

### Health Endpoints:
- **Worker Status**: `/health/workers`
- **Queue Status**: `/health/queues`
- **Task Statistics**: `/admin/celery/stats`

## Best Practices

### 1. Idempotency
- All tasks should be idempotent
- Handle duplicate execution gracefully
- Use database constraints for uniqueness

### 2. Error Handling
- Comprehensive error logging
- Graceful degradation
- Automatic retry with backoff

### 3. Performance
- Batch processing where possible
- Efficient database queries
- Memory management and cleanup

### 4. Monitoring
- Track all operations
- Monitor queue depths
- Alert on failures

## Troubleshooting

### Common Issues:

#### 1. Race Conditions
- **Symptoms**: "Invalid sync status" errors
- **Cause**: Multiple tasks processing same routing
- **Solution**: Implemented double validation and status marking

#### 2. Duplicate Tasks
- **Symptoms**: Same job processed multiple times
- **Cause**: OutboxWorker enqueuing duplicates
- **Solution**: Implemented routing tracking and duplicate prevention

#### 3. Event Loop Issues
- **Symptoms**: "Event loop is closed" errors
- **Cause**: Async operations in Celery tasks
- **Solution**: Implemented `run_async_in_new_loop` function

### Debug Commands:
```bash
# Check Celery worker status
celery -A src.background.celery_app worker --loglevel=info

# Check Celery Beat status
celery -A src.background.celery_app beat --loglevel=info

# Monitor queues
celery -A src.background.celery_app inspect active

# Check task results
celery -A src.background.celery_app inspect stats
```

## Future Improvements

### 1. Enhanced Monitoring
- Prometheus metrics integration
- Grafana dashboards
- Alerting system

### 2. Performance Optimization
- Connection pooling
- Batch processing improvements
- Cache integration

### 3. Scalability
- Horizontal scaling
- Load balancing
- Auto-scaling based on queue depth

### 4. Reliability
- Circuit breaker pattern
- Dead letter queues
- Advanced retry strategies
