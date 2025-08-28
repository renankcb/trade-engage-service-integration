"""
Prometheus metrics for system monitoring.
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, 
    generate_latest, CONTENT_TYPE_LATEST,
    multiprocess, CollectorRegistry
)
import time
from functools import wraps
from typing import Callable, Any
import asyncio

# Create a multiprocess registry for Celery workers
registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

# Job-related metrics
JOBS_CREATED = Counter(
    'jobs_created_total',
    'Total number of jobs created',
    ['category', 'company_id'],
    registry=registry
)

JOBS_SYNCED = Counter(
    'jobs_synced_total',
    'Total number of jobs synced to providers',
    ['provider_type', 'company_id', 'status'],
    registry=registry
)

JOB_SYNC_DURATION = Histogram(
    'job_sync_duration_seconds',
    'Time spent syncing jobs to providers',
    ['provider_type', 'company_id'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry
)

JOB_ROUTINGS_CREATED = Counter(
    'job_routings_created_total',
    'Total number of job routings created',
    ['company_id', 'matching_score_range'],
    registry=registry
)

# Worker performance metrics
WORKER_TASKS_PROCESSED = Counter(
    'worker_tasks_processed_total',
    'Total number of tasks processed by workers',
    ['worker_type', 'task_type', 'status'],
    registry=registry
)

WORKER_TASK_DURATION = Histogram(
    'worker_task_duration_seconds',
    'Time spent processing tasks by workers',
    ['worker_type', 'task_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry
)

WORKER_QUEUE_SIZE = Gauge(
    'worker_queue_size',
    'Current size of worker queues',
    ['queue_name'],
    registry=registry
)

# Outbox metrics
OUTBOX_EVENTS_CREATED = Counter(
    'outbox_events_created_total',
    'Total number of outbox events created',
    ['event_type', 'status'],
    registry=registry
)

OUTBOX_EVENTS_PROCESSED = Counter(
    'outbox_events_processed_total',
    'Total number of outbox events processed',
    ['event_type', 'status'],
    registry=registry
)

OUTBOX_PROCESSING_DURATION = Histogram(
    'outbox_processing_duration_seconds',
    'Time spent processing outbox events',
    ['event_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    registry=registry
)

# Provider integration metrics
PROVIDER_API_CALLS = Counter(
    'provider_api_calls_total',
    'Total number of API calls to providers',
    ['provider_type', 'endpoint', 'status_code'],
    registry=registry
)

PROVIDER_API_DURATION = Histogram(
    'provider_api_duration_seconds',
    'Time spent making API calls to providers',
    ['provider_type', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=registry
)

PROVIDER_RATE_LIMIT_HITS = Counter(
    'provider_rate_limit_hits_total',
    'Total number of rate limit hits by provider',
    ['provider_type', 'endpoint'],
    registry=registry
)

# Error and retry metrics
ERRORS_TOTAL = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component', 'severity'],
    registry=registry
)

RETRY_ATTEMPTS = Counter(
    'retry_attempts_total',
    'Total number of retry attempts',
    ['operation_type', 'component'],
    registry=registry
)

CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Current state of circuit breakers',
    ['operation_type', 'component'],
    registry=registry
)

# System health metrics
SYSTEM_UP_TIME = Gauge(
    'system_up_time_seconds',
    'System uptime in seconds',
    registry=registry
)

ACTIVE_WORKERS = Gauge(
    'active_workers',
    'Number of currently active workers',
    ['worker_type'],
    registry=registry
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections',
    'Number of active database connections',
    registry=registry
)

REDIS_CONNECTIONS = Gauge(
    'redis_connections',
    'Number of active Redis connections',
    registry=registry
)

# Business metrics
LEADS_DELIVERED = Counter(
    'leads_delivered_total',
    'Total number of leads delivered to companies',
    ['company_id', 'provider_type', 'delivery_time_range'],
    registry=registry
)

LEAD_DELIVERY_DURATION = Histogram(
    'lead_delivery_duration_seconds',
    'Time from job creation to lead delivery',
    ['company_id', 'provider_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry
)

MATCHING_SCORES = Histogram(
    'job_matching_scores',
    'Distribution of job matching scores',
    ['category', 'company_id'],
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    registry=registry
)


def track_metrics(metric_type: str, **labels):
    """
    Decorator to track metrics for functions.
    
    Args:
        metric_type: Type of metric to track ('counter', 'histogram', 'gauge')
        **labels: Labels to apply to the metric
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Track success metrics
                if metric_type == 'counter':
                    JOBS_SYNCED.labels(
                        provider_type=labels.get('provider_type', 'unknown'),
                        company_id=labels.get('company_id', 'unknown'),
                        status='success'
                    ).inc()
                elif metric_type == 'histogram':
                    JOB_SYNC_DURATION.labels(
                        provider_type=labels.get('provider_type', 'unknown'),
                        company_id=labels.get('company_id', 'unknown')
                    ).observe(time.time() - start_time)
                
                return result
                
            except Exception as e:
                # Track error metrics
                ERRORS_TOTAL.labels(
                    error_type=type(e).__name__,
                    component=labels.get('component', 'unknown'),
                    severity='error'
                ).inc()
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Track success metrics
                if metric_type == 'counter':
                    JOBS_SYNCED.labels(
                        provider_type=labels.get('provider_type', 'unknown'),
                        company_id=labels.get('company_id', 'unknown'),
                        status='success'
                    ).inc()
                elif metric_type == 'histogram':
                    JOB_SYNC_DURATION.labels(
                        provider_type=labels.get('provider_type', 'unknown'),
                        company_id=labels.get('company_id', 'unknown')
                    ).observe(time.time() - start_time)
                
                return result
                
            except Exception as e:
                # Track error metrics
                ERRORS_TOTAL.labels(
                    error_type=type(e).__name__,
                    component=labels.get('component', 'unknown'),
                    severity='error'
                ).inc()
                
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def record_job_creation(category: str, company_id: str):
    """Record job creation metric."""
    JOBS_CREATED.labels(category=category, company_id=company_id).inc()


def record_job_sync(provider_type: str, company_id: str, status: str):
    """Record job sync metric."""
    JOBS_SYNCED.labels(
        provider_type=provider_type,
        company_id=company_id,
        status=status
    ).inc()


def record_job_routing_creation(company_id: str, matching_score: float):
    """Record job routing creation metric."""
    # Categorize matching score
    if matching_score >= 0.8:
        score_range = "high"
    elif matching_score >= 0.6:
        score_range = "medium"
    elif matching_score >= 0.4:
        score_range = "low"
    else:
        score_range = "very_low"
    
    JOB_ROUTINGS_CREATED.labels(
        company_id=company_id,
        matching_score_range=score_range
    ).inc()


def record_worker_task(worker_type: str, task_type: str, status: str):
    """Record worker task processing metric."""
    WORKER_TASKS_PROCESSED.labels(
        worker_type=worker_type,
        task_type=task_type,
        status=status
    ).inc()


def record_outbox_event_creation(event_type: str, status: str):
    """Record outbox event creation metric."""
    OUTBOX_EVENTS_CREATED.labels(
        event_type=event_type,
        status=status
    ).inc()


def record_outbox_event_processing(event_type: str, status: str):
    """Record outbox event processing metric."""
    OUTBOX_EVENTS_PROCESSED.labels(
        event_type=event_type,
        status=status
    ).inc()


def record_provider_api_call(provider_type: str, endpoint: str, status_code: int):
    """Record provider API call metric."""
    PROVIDER_API_CALLS.labels(
        provider_type=provider_type,
        endpoint=endpoint,
        status_code=status_code
    ).inc()


def record_provider_rate_limit_hit(provider_type: str, endpoint: str):
    """Record provider rate limit hit metric."""
    PROVIDER_RATE_LIMIT_HITS.labels(
        provider_type=provider_type,
        endpoint=endpoint
    ).inc()


def record_error(error_type: str, component: str, severity: str = 'error'):
    """Record error metric."""
    ERRORS_TOTAL.labels(
        error_type=error_type,
        component=component,
        severity=severity
    ).inc()


def record_retry_attempt(operation_type: str, component: str):
    """Record retry attempt metric."""
    RETRY_ATTEMPTS.labels(
        operation_type=operation_type,
        component=component
    ).inc()


def set_circuit_breaker_state(operation_type: str, component: str, state: str):
    """Set circuit breaker state metric."""
    # Convert state to numeric value
    state_value = {
        'closed': 0,
        'half_open': 1,
        'open': 2
    }.get(state, 0)
    
    CIRCUIT_BREAKER_STATE.labels(
        operation_type=operation_type,
        component=component
    ).set(state_value)


def set_worker_count(worker_type: str, count: int):
    """Set active worker count metric."""
    ACTIVE_WORKERS.labels(worker_type=worker_type).set(count)


def set_queue_size(queue_name: str, size: int):
    """Set queue size metric."""
    WORKER_QUEUE_SIZE.labels(queue_name=queue_name).set(size)


def record_lead_delivery(company_id: str, provider_type: str, delivery_time: float):
    """Record lead delivery metric."""
    LEADS_DELIVERED.labels(
        company_id=company_id,
        provider_type=provider_type,
        delivery_time_range='within_5min' if delivery_time <= 300 else 'over_5min'
    ).inc()
    
    LEAD_DELIVERY_DURATION.labels(
        company_id=company_id,
        provider_type=provider_type
    ).observe(delivery_time)


def record_matching_score(category: str, company_id: str, score: float):
    """Record job matching score metric."""
    MATCHING_SCORES.labels(
        category=category,
        company_id=company_id
    ).observe(score)


def get_metrics():
    """Get all metrics in Prometheus format."""
    return generate_latest(registry)


def get_metrics_content_type():
    """Get the content type for metrics."""
    return CONTENT_TYPE_LATEST
