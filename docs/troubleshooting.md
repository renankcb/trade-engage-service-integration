# 🐛 Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting steps for common issues that may arise when using the TradeEngage Service Integration Service.

## 🚨 Emergency Procedures

### Complete System Reset
If the system is completely unresponsive:

```bash
# Stop all services
make down

# Remove all containers and volumes
make clean

# Start fresh
make setup
```

### Database Recovery
If the database is corrupted or inaccessible:

```bash
# Backup current data (if possible)
make db-backup

# Reset database
make db-reset

# Restore from backup if needed
# (manual process - see deployment docs)
```

## 🔍 Diagnostic Commands

### System Status
```bash
# Check overall system health
make health

# View service status
make status

# Check all service logs
make logs
```

### Service-Specific Logs
```bash
# API logs
make logs-api

# Worker logs
make logs-worker

# Scheduler logs
make logs-scheduler

# Database logs
docker logs service-integration-postgres-1

# Redis logs
docker logs service-integration-redis-1
```

## 🗄️ Database Issues

### Connection Failures

**Symptoms:**
- API returns 500 errors
- Health checks fail
- Migration commands fail
- Error: "connection refused" or "authentication failed"

**Solutions:**

1. **Start Database Services:**
   ```bash
   make db-up
   ```

2. **Check Database Health:**
   ```bash
   make health
   ```

3. **Verify Database Connection:**
   ```bash
   make db-shell
   # Then run: SELECT 1;
   ```

4. **Check Database Logs:**
   ```bash
   docker logs service-integration-postgres-1
   ```

5. **Test Database Connection:**
   ```bash
   docker exec service-integration-postgres-1 psql -U integration_user -d integration_service -c "SELECT 1;"
   ```

**Debug Commands:**
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# Check container health
docker inspect service-integration-postgres-1 | grep -A 10 "Health"

# Check database port
docker port service-integration-postgres-1

# Test network connectivity
docker exec service-integration-postgres-1 ping localhost
```

### Migration Issues

**Symptoms:**
- Database schema errors
- Missing tables
- Column type mismatches
- Error: "relation does not exist"

**Solutions:**

1. **Check Migration Status:**
   ```bash
   make migrate-status
   ```

2. **Run Migrations:**
   ```bash
   make migrate
   ```

3. **Reset Database (⚠️ destructive):**
   ```bash
   make db-reset
   ```

4. **Manual Migration:**
   ```bash
   poetry run alembic upgrade head
   ```

**Debug Commands:**
```bash
# Check current migration version
poetry run alembic current

# View migration history
poetry run alembic history

# Check migration files
ls -la migrations/versions/
```

### Schema Validation

**Symptoms:**
- Data insertion errors
- Constraint violations
- Foreign key errors

**Solutions:**

1. **Verify Table Structure:**
   ```bash
   make db-shell
   # Then run:
   \d jobs
   \d job_routings
   \d companies
   \d technicians
   ```

2. **Check Constraints:**
   ```bash
   # In database shell
   SELECT conname, contype, pg_get_constraintdef(oid) 
   FROM pg_constraint 
   WHERE conrelid = 'jobs'::regclass;
   ```

## 🔴 Redis Issues

### Connection Failures

**Symptoms:**
- Celery workers not processing tasks
- Task queue not working
- Scheduler not executing
- Error: "Redis connection failed"

**Solutions:**

1. **Start Redis Service:**
   ```bash
   make db-up
   ```

2. **Check Redis Health:**
   ```bash
   docker exec service-integration-redis-1 redis-cli ping
   ```

3. **Restart Redis if Needed:**
   ```bash
   docker restart service-integration-redis-1
   ```

**Debug Commands:**
```bash
# Check Redis logs
docker logs service-integration-redis-1

# Monitor Redis operations
docker exec service-integration-redis-1 redis-cli monitor

# Check Redis info
docker exec service-integration-redis-1 redis-cli info

# Test Redis connectivity
docker exec service-integration-redis-1 redis-cli -h localhost -p 6379 ping
```

### Queue Issues

**Symptoms:**
- Tasks stuck in queue
- Workers not picking up tasks
- High memory usage

**Solutions:**

1. **Check Queue Status:**
   ```bash
   curl "http://localhost:8000/api/admin/queue-stats"
   ```

2. **Clear Queues (if needed):**
   ```bash
   curl -X POST "http://localhost:8000/api/admin/clear-queues"
   ```

3. **Restart Workers:**
   ```bash
   make worker-docker
   ```

## 🌐 External API Issues (ServiceTitan)

### Authentication Failures

**Symptoms:**
- Job routings stuck in 'pending' status
- Sync errors in logs
- High retry counts
- Error: "Invalid credentials" or "Unauthorized"

**Solutions:**

1. **Verify Environment Variables:**
   ```bash
   # Check if ServiceTitan credentials are set
   echo $SERVICETITAN_CLIENT_ID
   echo $SERVICETITAN_CLIENT_SECRET
   echo $SERVICETITAN_TENANT_ID
   ```

2. **Check Provider Configuration:**
   ```bash
   curl "http://localhost:8000/api/admin/providers"
   ```

3. **Test Provider Connection:**
   ```bash
   curl "http://localhost:8000/api/health/component/providers"
   ```

4. **Review Error Logs:**
   ```bash
   make logs-api | grep -i "servicetitan\|error\|exception"
   ```

**Debug Steps:**

1. **Check API Credentials:**
   ```bash
   # Verify credentials in .env file
   cat .env | grep SERVICETITAN
   ```

2. **Test ServiceTitan API Directly:**
   ```bash
   # Test with curl (replace with actual credentials)
   curl -X POST "https://api.servicetitan.io/oauth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
   ```

3. **Check Network Connectivity:**
   ```bash
   # Test external connectivity
   curl -I "https://api.servicetitan.io"
   ```

### Rate Limiting Issues

**Symptoms:**
- Intermittent sync failures
- Error: "Rate limit exceeded"
- Tasks failing with 429 status

**Solutions:**

1. **Check Rate Limit Status:**
   ```bash
   curl "http://localhost:8000/api/admin/rate-limits"
   ```

2. **Adjust Rate Limiting:**
   ```bash
   # Check current configuration
   grep -r "rate_limit" src/
   ```

3. **Implement Backoff Strategy:**
   - System automatically implements exponential backoff
   - Failed tasks are retried with increasing delays

## ⚙️ Celery Issues

### Worker Failures

**Symptoms:**
- Tasks not executing
- Workers not responding
- Scheduler not running
- Error: "Worker not available"

**Solutions:**

1. **Start Workers and Scheduler:**
   ```bash
   make worker-docker
   make scheduler-docker
   ```

2. **Check Worker Status:**
   ```bash
   make logs-worker
   ```

3. **Check Scheduler Status:**
   ```bash
   make logs-scheduler
   ```

**Debug Commands:**

1. **Check Celery Status:**
   ```bash
   docker exec service-integration-worker-1 celery -A src.background.celery_app status
   ```

2. **View Task Queue:**
   ```bash
   docker exec service-integration-worker-1 celery -A src.background.celery_app inspect active
   ```

3. **Check Worker Processes:**
   ```bash
   docker exec service-integration-worker-1 ps aux | grep celery
   ```

4. **Monitor Task Execution:**
   ```bash
   docker exec service-integration-worker-1 celery -A src.background.celery_app inspect stats
   ```

### Task Failures

**Symptoms:**
- Tasks failing repeatedly
- High error rates
- Tasks stuck in queue

**Solutions:**

1. **Check Task Logs:**
   ```bash
   make logs-worker | grep -i "error\|exception\|failed"
   ```

2. **Retry Failed Tasks:**
   ```bash
   # Check failed routings
   curl "http://localhost:8000/api/routings/status/failed"
   
   # Retry specific routing
   curl -X POST "http://localhost:8000/api/routings/{routing_id}/retry"
   ```

3. **Clear Failed Tasks:**
   ```bash
   # Clear all queues
   curl -X POST "http://localhost:8000/api/admin/clear-queues"
   ```

## 📊 Job Routing Issues

### Jobs Not Being Routed

**Symptoms:**
- Jobs created but no routings
- Routings not syncing
- Status not updating

**Debug Steps:**

1. **Check Job Creation:**
   ```bash
   # Create a test job
   curl -X POST "http://localhost:8000/api/jobs/" \
     -H "Content-Type: application/json" \
     -d '{
       "summary": "Test job",
       "address": {"street": "123 Test St", "city": "Test City", "state": "CA", "zip_code": "90210"},
       "homeowner": {"name": "Test User", "phone": "555-0000", "email": "test@example.com"},
       "created_by_company_id": "your-company-uuid",
       "created_by_technician_id": "your-tech-uuid"
     }'
   ```

2. **Check Routing Status:**
   ```bash
   # List all routings
   curl "http://localhost:8000/api/jobs/routings"
   ```

3. **Check Sync Status:**
   ```bash
   # View pending routings
   curl "http://localhost:8000/api/routings/status/pending"
   ```

4. **Verify Company Configuration:**
   ```bash
   # Check if companies have providers configured
   curl "http://localhost:8000/api/admin/companies"
   ```

### Sync Failures

**Symptoms:**
- Routings stuck in 'pending' status
- High retry counts
- Error messages in logs

**Debug Steps:**

1. **Check Provider Health:**
   ```bash
   curl "http://localhost:8000/api/health/component/providers"
   ```

2. **Review Sync Logs:**
   ```bash
   make logs-worker | grep -i "sync\|servicetitan"
   ```

3. **Check Rate Limits:**
   ```bash
   curl "http://localhost:8000/api/admin/rate-limits"
   ```

4. **Verify External IDs:**
   ```bash
   # Check if external IDs are being stored
   curl "http://localhost:8000/api/routings/status/synced"
   ```

## 🚀 Performance Issues

### Slow API Responses

**Symptoms:**
- API requests taking > 1 second
- Timeout errors
- High response times

**Solutions:**

1. **Check System Resources:**
   ```bash
   make status
   ```

2. **Monitor Database Performance:**
   ```bash
   make db-shell
   # Then run:
   SELECT * FROM pg_stat_activity;
   SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```

3. **Check Queue Depths:**
   ```bash
   curl "http://localhost:8000/api/admin/queue-stats"
   ```

4. **Monitor Memory Usage:**
   ```bash
   docker stats
   ```

### High Memory Usage

**Symptoms:**
- Container memory usage > 80%
- Out of memory errors
- Slow performance

**Solutions:**

1. **Check Memory Usage:**
   ```bash
   docker stats --no-stream
   ```

2. **Restart Memory-Intensive Services:**
   ```bash
   docker restart service-integration-api-1
   docker restart service-integration-worker-1
   ```

3. **Check for Memory Leaks:**
   ```bash
   make logs-api | grep -i "memory\|leak"
   ```

## 🔧 Configuration Issues

### Environment Variables

**Symptoms:**
- Service won't start
- Configuration errors
- Missing credentials

**Solutions:**

1. **Verify .env File:**
   ```bash
   # Check if .env exists
   ls -la .env
   
   # Verify required variables
   cat .env | grep -E "DATABASE_URL|SERVICETITAN|REDIS_URL"
   ```

2. **Check Variable Format:**
   ```bash
   # Ensure no extra spaces or quotes
   cat .env | grep "="
   ```

3. **Reload Environment:**
   ```bash
   # Restart services to pick up new environment
   make restart
   ```

### Database Configuration

**Symptoms:**
- Connection string errors
- Authentication failures
- Wrong database

**Solutions:**

1. **Verify DATABASE_URL:**
   ```bash
   echo $DATABASE_URL
   # Should look like: postgresql://user:pass@host:port/db
   ```

2. **Test Connection String:**
   ```bash
   # Test with psql
   psql "$DATABASE_URL" -c "SELECT 1;"
   ```

3. **Check Database Exists:**
   ```bash
   make db-shell
   # Then run: \l
   ```

## 📝 Log Analysis

### Common Error Patterns

1. **Connection Refused:**
   ```
   connection to server at "localhost" (::1), port 5432 failed: Connection refused
   ```
   **Solution:** Start database services with `make db-up`

2. **Authentication Failed:**
   ```
   FATAL: password authentication failed for user "integration_user"
   ```
   **Solution:** Check DATABASE_URL in .env file

3. **Rate Limit Exceeded:**
   ```
   Rate limit exceeded. Try again in 60 seconds.
   ```
   **Solution:** Wait for rate limit to reset or adjust limits

4. **Task Timeout:**
   ```
   Task timed out after 30.0 seconds
   ```
   **Solution:** Check external API response times or increase timeout

### Log Filtering

```bash
# Filter by error level
make logs-api | grep -i "error"

# Filter by specific service
make logs | grep -i "servicetitan"

# Filter by time
make logs-api | grep "$(date +%Y-%m-%d)"

# Filter by specific error
make logs-worker | grep -i "connection refused\|timeout\|rate limit"
```

## 🆘 Getting Help

### Before Asking for Help

1. **Check Logs First:**
   ```bash
   make logs          # All services
   make logs-api      # API only
   make logs-worker   # Workers only
   ```

2. **Verify Configuration:**
   ```bash
   make health        # Overall health
   make status        # Service status
   ```

3. **Try Common Commands:**
   ```bash
   make help          # Show all commands
   make restart       # Restart all services
   make shell         # Debug shell
   ```

### Information to Provide

When asking for help, include:

1. **Error Messages:** Exact error text from logs
2. **Environment:** Development/Staging/Production
3. **Steps to Reproduce:** What you were doing when it failed
4. **System Status:** Output of `make health` and `make status`
5. **Recent Changes:** What changed before the issue started

### Contact Information

- **Repository Issues:** Create an issue in the GitHub repository
- **Development Team:** Contact the development team directly
- **Documentation:** Check this troubleshooting guide and other docs first

---

**Remember:** Most issues can be resolved by checking logs, restarting services, and verifying configuration. When in doubt, start with `make health` and `make logs`.
