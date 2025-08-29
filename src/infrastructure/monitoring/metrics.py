"""
Prometheus metrics for system monitoring.
"""

import asyncio
import os
import time
from functools import wraps
from typing import Any, Callable

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    multiprocess,
)

# Initialize multiprocess collector only if PROMETHEUS_MULTIPROC_DIR is available
registry = CollectorRegistry()
prometheus_multiproc_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR")

if prometheus_multiproc_dir:
    try:
        # Ensure directory exists and has correct permissions
        os.makedirs(prometheus_multiproc_dir, exist_ok=True)

        # Set permissions to be writable by all users (for Docker containers)
        try:
            os.chmod(prometheus_multiproc_dir, 0o777)
        except Exception as e:
            print(f"Warning: Could not set directory permissions: {e}")

        # Check if directory is writable
        if os.access(prometheus_multiproc_dir, os.W_OK):
            if os.path.isdir(prometheus_multiproc_dir):
                try:
                    multiprocess.MultiProcessCollector(registry)
                    print(
                        f"Multiprocess collector initialized successfully in {prometheus_multiproc_dir}"
                    )
                except Exception as e:
                    print(f"Warning: Failed to initialize multiprocess collector: {e}")
                    # Fallback to single process registry
                    registry = CollectorRegistry()
            else:
                print(
                    f"Warning: PROMETHEUS_MULTIPROC_DIR is not a directory: {prometheus_multiproc_dir}"
                )
                registry = CollectorRegistry()
        else:
            print(
                f"Warning: PROMETHEUS_MULTIPROC_DIR is not writable: {prometheus_multiproc_dir}"
            )
            registry = CollectorRegistry()
    except Exception as e:
        print(f"Warning: Failed to setup multiprocess collector: {e}")
        registry = CollectorRegistry()
else:
    print("PROMETHEUS_MULTIPROC_DIR not set, using single process registry")
    registry = CollectorRegistry()


# Initialize metrics with lazy loading to avoid permission issues
def get_registry():
    """Get the current registry, ensuring it's properly initialized."""
    return registry


# Use lazy initialization for metrics that might cause permission issues
def _get_metric(metric_class, *args, **kwargs):
    """Lazy initialization of metrics to avoid permission issues."""
    try:
        return metric_class(*args, **kwargs, registry=get_registry())
    except Exception as e:
        print(f"Warning: Failed to create metric {metric_class.__name__}: {e}")

        # Return a dummy metric that does nothing
        class DummyMetric:
            def __init__(self, *args, **kwargs):
                pass

            def __call__(self, *args, **kwargs):
                pass

            def labels(self, *args, **kwargs):
                return self

            def set(self, value):
                pass

            def inc(self, amount=1):
                pass

            def observe(self, value):
                pass

        return DummyMetric()


# Initialize metrics with error handling
try:
    JOBS_CREATED = _get_metric(
        Counter,
        "jobs_created_total",
        "Total number of jobs created",
        ["category", "company_id"],
    )

    JOBS_SYNCED = _get_metric(
        Counter,
        "jobs_synced_total",
        "Total number of jobs synced to providers",
        ["provider_type", "company_id", "status"],
    )

    JOB_SYNC_DURATION = _get_metric(
        Histogram,
        "job_sync_duration_seconds",
        "Time spent syncing jobs to providers",
        ["provider_type", "company_id"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    JOB_ROUTINGS_CREATED = _get_metric(
        Counter,
        "job_routings_created_total",
        "Total number of job routings created",
        ["company_id", "matching_score_range"],
    )

    # Worker performance metrics
    WORKER_TASKS_PROCESSED = _get_metric(
        Counter,
        "worker_tasks_processed_total",
        "Total number of tasks processed by workers",
        ["worker_type", "task_type", "status"],
    )

    WORKER_TASK_DURATION = _get_metric(
        Histogram,
        "worker_task_duration_seconds",
        "Time spent processing tasks by workers",
        ["worker_type", "task_type"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    # System health metrics
    SYSTEM_UP_TIME = _get_metric(
        Gauge,
        "system_up_time_seconds",
        "System uptime in seconds",
    )

    ACTIVE_WORKERS = _get_metric(
        Gauge,
        "active_workers",
        "Number of currently active workers",
        ["worker_type"],
    )

    DATABASE_CONNECTIONS = _get_metric(
        Gauge,
        "database_connections",
        "Number of active database connections",
    )

    REDIS_CONNECTIONS = _get_metric(
        Gauge,
        "redis_connections",
        "Number of active Redis connections",
    )

    # API metrics
    API_REQUESTS = _get_metric(
        Counter,
        "api_requests_total",
        "Total number of API requests",
        ["method", "endpoint", "status_code"],
    )

    API_REQUEST_DURATION = _get_metric(
        Histogram,
        "api_request_duration_seconds",
        "Time spent processing API requests",
        ["method", "endpoint"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    )

    # Error metrics
    ERRORS_TOTAL = _get_metric(
        Counter,
        "errors_total",
        "Total number of errors",
        ["error_type", "component"],
    )

    # Rate limiting metrics
    RATE_LIMIT_HITS = _get_metric(
        Counter,
        "rate_limit_hits_total",
        "Total number of rate limit hits",
        ["rate_limit_key", "client_id"],
    )

    # Retry metrics
    RETRY_ATTEMPTS = _get_metric(
        Counter,
        "retry_attempts_total",
        "Total number of retry attempts",
        ["operation", "retry_count"],
    )

    # Circuit breaker metrics
    CIRCUIT_BREAKER_STATE = _get_metric(
        Gauge,
        "circuit_breaker_state",
        "Current state of circuit breaker",
        ["operation"],
    )

    CIRCUIT_BREAKER_TRIPS = _get_metric(
        Counter,
        "circuit_breaker_trips_total",
        "Total number of circuit breaker trips",
        ["operation"],
    )

except Exception as e:
    print(f"Warning: Failed to initialize metrics: {e}")

    # Create dummy metrics to prevent crashes
    class DummyMetric:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def set(self, value):
            pass

        def inc(self, amount=1):
            pass

        def observe(self, value):
            pass

    JOBS_CREATED = DummyMetric()
    JOBS_SYNCED = DummyMetric()
    JOB_SYNC_DURATION = DummyMetric()
    JOB_ROUTINGS_CREATED = DummyMetric()
    WORKER_TASKS_PROCESSED = DummyMetric()
    WORKER_TASK_DURATION = DummyMetric()
    SYSTEM_UP_TIME = DummyMetric()
    ACTIVE_WORKERS = DummyMetric()
    DATABASE_CONNECTIONS = DummyMetric()
    REDIS_CONNECTIONS = DummyMetric()
    API_REQUESTS = DummyMetric()
    API_REQUEST_DURATION = DummyMetric()
    ERRORS_TOTAL = DummyMetric()
    RATE_LIMIT_HITS = DummyMetric()
    RETRY_ATTEMPTS = DummyMetric()
    CIRCUIT_BREAKER_STATE = DummyMetric()
    CIRCUIT_BREAKER_TRIPS = DummyMetric()


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
                if metric_type == "counter":
                    JOBS_SYNCED.labels(
                        provider_type=labels.get("provider_type", "unknown"),
                        company_id=labels.get("company_id", "unknown"),
                        status="success",
                    ).inc()
                elif metric_type == "histogram":
                    JOB_SYNC_DURATION.labels(
                        provider_type=labels.get("provider_type", "unknown"),
                        company_id=labels.get("company_id", "unknown"),
                    ).observe(time.time() - start_time)

                return result

            except Exception as e:
                # Track error metrics
                ERRORS_TOTAL.labels(
                    error_type=type(e).__name__,
                    component=labels.get("component", "unknown"),
                    severity="error",
                ).inc()

                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Track success metrics
                if metric_type == "counter":
                    JOBS_SYNCED.labels(
                        provider_type=labels.get("provider_type", "unknown"),
                        company_id=labels.get("company_id", "unknown"),
                        status="success",
                    ).inc()
                elif metric_type == "histogram":
                    JOB_SYNC_DURATION.labels(
                        provider_type=labels.get("provider_type", "unknown"),
                        company_id=labels.get("company_id", "unknown"),
                    ).observe(time.time() - start_time)

                return result

            except Exception as e:
                # Track error metrics
                ERRORS_TOTAL.labels(
                    error_type=type(e).__name__,
                    component=labels.get("component", "unknown"),
                    severity="error",
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
        provider_type=provider_type, company_id=company_id, status=status
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
        company_id=company_id, matching_score_range=score_range
    ).inc()


def record_worker_task(worker_type: str, task_type: str, status: str):
    """Record worker task processing metric."""
    WORKER_TASKS_PROCESSED.labels(
        worker_type=worker_type, task_type=task_type, status=status
    ).inc()


def record_outbox_event_creation(event_type: str, status: str):
    """Record outbox event creation metric."""
    # Use a generic metric since OUTBOX_EVENTS_CREATED was removed
    JOBS_CREATED.labels(category="outbox_event", company_id=event_type).inc()


def record_outbox_event_processing(event_type: str, status: str):
    """Record outbox event processing metric."""
    # Use a generic metric since OUTBOX_EVENTS_PROCESSED was removed
    WORKER_TASKS_PROCESSED.labels(
        worker_type="outbox", task_type=event_type, status=status
    ).inc()


def record_provider_api_call(provider_type: str, endpoint: str, status_code: int):
    """Record provider API call metric."""
    # Use a generic metric since PROVIDER_API_CALLS was removed
    API_REQUESTS.labels(
        method="POST", endpoint=f"{provider_type}_{endpoint}", status_code=status_code
    ).inc()


def record_provider_rate_limit_hit(provider_type: str, endpoint: str):
    """Record provider rate limit hit metric."""
    # Use a generic metric since PROVIDER_RATE_LIMIT_HITS was removed
    RATE_LIMIT_HITS.labels(
        rate_limit_key=f"{provider_type}_{endpoint}", client_id="provider"
    ).inc()


def record_error(error_type: str, component: str, severity: str = "error"):
    """Record error metric."""
    ERRORS_TOTAL.labels(error_type=error_type, component=component).inc()


def record_retry_attempt(operation_type: str, component: str):
    """Record retry attempt metric."""
    RETRY_ATTEMPTS.labels(operation=operation_type, retry_count=1).inc()


def set_circuit_breaker_state(operation_type: str, component: str, state: str):
    """Set circuit breaker state metric."""
    # Convert state to numeric value
    state_value = {"closed": 0, "half_open": 1, "open": 2}.get(state, 0)

    CIRCUIT_BREAKER_STATE.labels(operation=operation_type).set(state_value)


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
        delivery_time_range="within_5min" if delivery_time <= 300 else "over_5min",
    ).inc()

    LEAD_DELIVERY_DURATION.labels(
        company_id=company_id, provider_type=provider_type
    ).observe(delivery_time)


def record_matching_score(category: str, company_id: str, score: float):
    """Record job matching score metric."""
    MATCHING_SCORES.labels(category=category, company_id=company_id).observe(score)


def get_metrics():
    """Get all metrics in Prometheus format."""
    return generate_latest(registry)


def get_metrics_content_type():
    """Get the content type for metrics."""
    return CONTENT_TYPE_LATEST
