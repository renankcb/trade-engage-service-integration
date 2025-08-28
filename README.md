# TradeEngage Service Integration

A production-ready integration service that connects TradeEngage with external Point of Sale (PoS) providers like ServiceTitan, designed for easy extensibility to additional providers.

## 🚀 **Key Features**

### **Intelligent Job Matching Engine**
- **Skill-based matching** between jobs and companies
- **Multi-level skill classification** (basic, intermediate, expert)
- **Category-based routing** (plumbing, HVAC, electrical, etc.)
- **Performance-optimized** with database indexes and efficient queries

### **Atomic Operations & Transactional Outbox**
- **100% atomic transactions** - all operations succeed or fail together
- **Transactional Outbox Pattern** ensures no events are lost
- **Guaranteed SLA compliance** - leads pushed within 5 minutes
- **Automatic rollback** on any failure

### **Provider Integration**
- **ServiceTitan integration** with real API endpoints
- **Mock provider** for testing and demonstration
- **Extensible architecture** for easy addition of new providers
- **Company-specific credentials** and configuration

### **Production Ready**
- **Comprehensive error handling** with retry mechanisms
- **Structured logging** for observability
- **Health checks** and monitoring endpoints
- **Rate limiting** and provider protection
- **Background task processing** with Celery

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Layer     │    │  Business Logic  │    │  Data Layer     │
│                 │    │                  │    │                 │
│ • FastAPI       │◄──►│ • Use Cases      │◄──►│ • PostgreSQL   │
│ • Validation    │    │ • Matching Engine│    │ • Redis        │
│ • Rate Limiting │    │ • Outbox Pattern │    │ • Migrations   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Background      │    │  Provider Layer  │    │  Monitoring     │
│ Processing      │    │                  │    │                 │
│                 │    │                  │    │                 │
│ • Celery Tasks  │    │ • ServiceTitan   │    │ • Prometheus    │
│ • Outbox Worker │    │ • Mock Provider  │    │ • Grafana       │
│ • Scheduling    │    │ • Factory Pattern│    │ • Health Checks │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔄 **Core Integration Flow**

### **1. Job Creation with Intelligent Matching**
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant UseCase
    participant MatchingEngine
    participant Database
    participant Outbox

    Client->>API: POST /jobs (with skills)
    API->>UseCase: CreateJobRequest
    UseCase->>MatchingEngine: Find matching companies
    MatchingEngine->>Database: Query companies + skills
    MatchingEngine-->>UseCase: Company matches (ranked)
    UseCase->>Database: Save job + routings (atomic)
    UseCase->>Outbox: Create sync events (atomic)
    UseCase-->>API: Job created + routings
    API-->>Client: 201 Created
```

### **2. Transactional Outbox Pattern**
```mermaid
sequenceDiagram
    participant UseCase
    participant Database
    participant Outbox
    participant Worker
    participant Celery
    participant Provider

    UseCase->>Database: Save job + routings
    UseCase->>Outbox: Create sync events
    Note over Database,Outbox: ATOMIC TRANSACTION
    Worker->>Outbox: Poll pending events
    Worker->>Celery: Enqueue sync tasks
    Celery->>Provider: Sync with external API
    Provider-->>Celery: Success/Failure
    Celery->>Database: Update routing status
```

### **3. SLA Guarantee: 5-Minute Lead Delivery**
```
Job Creation (0s) → Outbox Event (0s) → Worker (30s) → Celery (1s) → Provider (1-2s)
Total: ~32 seconds (well within 5-minute SLA)
```

## 📊 **Job Matching Algorithm**

### **Skill-Based Scoring**
- **Exact skill match**: +3.0 points
- **Skill level bonus**: +0.5 for exceeding requirements
- **Primary skill bonus**: +1.5 for company's primary skills
- **Provider bonus**: +0.3 for configured providers
- **Active status bonus**: +0.5 for active companies

### **Example Matching**
```json
{
  "job": {
    "required_skills": ["plumbing", "electrical"],
    "skill_levels": {"plumbing": "expert", "electrical": "intermediate"}
  },
  "company_matches": [
    {
      "company": "ABC Plumbing",
      "score": 4.8,
      "matched_skills": ["plumbing", "electrical"],
      "reason": "Perfect skill match + primary plumbing"
    },
    {
      "company": "XYZ Services",
      "score": 3.3,
      "matched_skills": ["electrical"],
      "reason": "Good electrical match, missing plumbing"
    }
  ]
}
```

## 🗄️ **Database Schema**

### **Core Tables**
- **`jobs`** - Job information with skills and category
- **`companies`** - Company details and provider associations
- **`company_skills`** - Skills and expertise levels per company
- **`job_routings`** - Job routing to companies with sync status
- **`outbox_events`** - Transactional outbox for reliable processing
- **`company_provider_associations`** - Provider configuration per company

### **Key Relationships**
```sql
-- Company with skills and provider
companies (1) ←→ (N) company_skills
companies (1) ←→ (1) company_provider_associations

-- Job routing with outbox events
jobs (1) ←→ (N) job_routings
job_routings (1) ←→ (1) outbox_events

-- Skills and categories
jobs (N) ←→ (1) job_categories
companies (N) ←→ (N) company_skills
```

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Docker & Docker Compose

### **1. Clone and Setup**
```bash
git clone <repository>
cd service-integration
poetry install
```

### **2. Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

### **3. Database Setup**
```bash
# Start services
make up

# Run migrations
make migrate

# Seed test data
make seed
```

### **4. Start the Service**
```bash
# Development
make dev

# Production
make start
```

## 📚 **API Documentation**

### **Create Job with Skills**
```bash
POST /jobs
{
  "summary": "Kitchen faucet replacement",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip_code": "12345"
  },
  "homeowner": {
    "name": "John Doe",
    "phone": "(555) 123-4567",
    "email": "john@example.com"
  },
  "created_by_company_id": "uuid-here",
  "created_by_technician_id": "uuid-here",
  "required_skills": ["plumbing"],
  "skill_levels": {"plumbing": "expert"},
  "category": "plumbing"
}
```

### **Response**
```json
{
  "id": "job-uuid",
  "summary": "Kitchen faucet replacement",
  "status": "pending",
  "matching_score": 4.5,
  "routings": [
    {
      "id": "routing-uuid",
      "company_id_received": "company-uuid",
      "sync_status": "pending"
    }
  ]
}
```

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/tradeengage

# Redis
REDIS_URL=redis://localhost:6379

# ServiceTitan
SERVICETITAN_CLIENT_ID=your_client_id
SERVICETITAN_CLIENT_SECRET=your_client_secret
SERVICETITAN_TENANT_ID=your_tenant_id

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### **Provider Configuration**
```json
{
  "servicetitan": {
    "base_url": "https://api.servicetitan.io",
    "timeout": 30,
    "retry_attempts": 3
  }
}
```

## 🧪 **Testing**

### **Run Tests**
```bash
# Unit tests
make test

# Integration tests
make test-integration

# E2E tests
make test-e2e

# Coverage report
make coverage
```

### **Test Data**
The system includes comprehensive test data:
- **Companies**: ABC Plumbing (ServiceTitan), XYZ HVAC (Mock)
- **Skills**: Plumbing, HVAC, Electrical, General Maintenance
- **Categories**: Plumbing, HVAC, Electrical, General
- **Sample Jobs**: Kitchen faucet, HVAC maintenance

## 📈 **Monitoring & Observability**

### **Health Checks**
- **`/health`** - Basic health status
- **`/health/ready`** - Readiness probe
- **`/health/live`** - Liveness probe

### **Metrics (Prometheus)**
- Job creation rate
- Matching success rate
- Sync latency
- Error rates by provider
- Queue depths

### **Logging**
Structured logging with correlation IDs:
```json
{
  "level": "INFO",
  "message": "Job created successfully",
  "job_id": "uuid",
  "matching_score": 4.5,
  "routings_count": 3,
  "correlation_id": "req-123"
}
```

## 🔄 **Background Processing**

### **Celery Tasks**
- **`sync_job_task`** - Sync individual job routing
- **`sync_pending_jobs_task`** - Batch sync pending routings
- **`poll_synced_jobs_task`** - Poll external providers for updates
- **`retry_failed_jobs_task`** - Retry failed syncs

### **Scheduling**
- **Outbox processing**: Every 30 seconds
- **Pending jobs sync**: Every 2 minutes
- **Status polling**: Every 30 minutes
- **Failed job retry**: Every 5 minutes

## 🚀 **Deployment**

### **Docker**
```bash
# Build and run
docker-compose up -d

# Scale workers
docker-compose up -d --scale worker=3
```

### **Production Considerations**
- **Database**: Use managed PostgreSQL (RDS, Cloud SQL)
- **Redis**: Use managed Redis (ElastiCache, Cloud Memorystore)
- **Monitoring**: Prometheus + Grafana stack
- **Logging**: Centralized logging (ELK, Cloud Logging)
- **Scaling**: Horizontal scaling with multiple worker instances

## 🔧 **Adding New Providers**

### **1. Implement Provider Interface**
```python
class NewProvider(ProviderInterface):
    async def create_lead(self, request: CreateLeadRequest) -> CreateLeadResponse:
        # Implementation here
        pass
    
    async def get_job_status(self, external_id: str) -> JobStatus:
        # Implementation here
        pass
```

### **2. Register in Factory**
```python
class ProviderFactory:
    def get_provider(self, provider_type: str) -> ProviderInterface:
        if provider_type == "new_provider":
            return NewProvider()
        # ... existing providers
```

### **3. Configure Company**
```sql
INSERT INTO company_provider_associations (
    company_id, provider_type, provider_config
) VALUES (
    'company-uuid', 'new_provider', '{"api_key": "..."}'
);
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License.

## 🆘 **Support**

For questions or issues:
- Create an issue in the repository
- Check the troubleshooting section below
- Review the API documentation

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Database Connection Errors**
```bash
# Check database status
make db-status

# Reset database
make db-reset
```

#### **Migration Issues**
```bash
# Check migration status
make migrate-status

# Reset migrations
make migrate-reset
```

#### **Provider Sync Failures**
```bash
# Check logs
make logs

# Retry failed jobs
make retry-failed
```

### **Debug Mode**
```bash
# Enable debug logging
LOG_LEVEL=DEBUG make dev

# Check outbox events
make check-outbox
```

## 📚 **Additional Resources**

- [API Documentation](./docs/api.md)
- [Architecture Decisions](./docs/architecture.md)
- [ServiceTitan API Docs](https://developer.servicetitan.io/apis/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)

## 🚀 **Job Sync Flow - Sincronização Inteligente com Providers**

### **Arquitetura do Job Sync Flow**

```
Job Created → Outbox Event → Worker Processing → Provider Sync → Status Update
     ↓              ↓              ↓              ↓            ↓
  Create Job   Transactional   Outbox Worker   Provider    Database
  with Skills     Outbox      (30s interval)   Manager    Update
```

### **Componentes do Job Sync Flow**

#### **1. Transactional Outbox Pattern**
- **Garantia de SLA**: Eventos processados a cada 30 segundos
- **Atomicidade**: Job + routings + outbox events em uma transação
- **Recuperação**: Sistema processa eventos pendentes automaticamente
- **Idempotência**: Evita duplicação de leads nos providers

#### **2. Background Workers**
- **Outbox Worker**: Processa eventos a cada 30s
- **Sync Worker**: Sincroniza jobs a cada 60s
- **Poll Worker**: Verifica updates a cada 5 minutos
- **Worker Manager**: Coordena todos os workers

#### **3. Rate Limiting & Circuit Breaker**
- **Rate Limiting**: 50 syncs/minuto por company
- **Circuit Breaker**: Abre após 5 falhas consecutivas
- **Retry Logic**: Exponential backoff com jitter
- **Fallback**: Graceful degradation em caso de falha

#### **4. Celery Tasks & Queues**
- **Queue Routing**: sync, poll, retry, maintenance
- **Task Scheduling**: Beat scheduler para tarefas periódicas
- **Worker Pools**: 4 workers concorrentes por padrão
- **Task Limits**: Timeouts configuráveis por tipo de task

### **Fluxo Detalhado de Sincronização**

#### **Fase 1: Job Creation & Outbox Event**
```python
# 1. Job é criado com skills e matching inteligente
job = await create_job_use_case.execute(request)

# 2. Outbox event é criado atomicamente
await outbox.create_event(
    event_type=OutboxEventType.JOB_SYNC,
    aggregate_id=str(routing.id),
    event_data={...}
)
```

#### **Fase 2: Outbox Worker Processing**
```python
# Worker processa eventos a cada 30 segundos
async def process_pending_events(self, batch_size: int = 50):
    events = await self.outbox.get_pending_events(limit=batch_size)
    
    for event in events:
        # Marca como processing (atomic)
        await self.outbox.mark_event_processing(event.id)
        
        # Processa evento
        success = await self._process_event(event)
        
        # Marca como completed/failed
        if success:
            await self.outbox.mark_event_completed(event.id)
        else:
            await self.outbox.mark_event_failed(event.id, error_msg)
```

#### **Fase 3: Celery Task Enqueueing**
```python
# Outbox worker enfileira Celery task
async def _process_job_sync_event(self, event: OutboxEvent):
    routing_id = event.event_data.get("routing_id")
    
    # Enfileira task para sync
    sync_job_task.delay(routing_id)
    
    return True
```

#### **Fase 4: Job Sync Execution**
```python
# Celery task executa sync com retry logic
@current_app.task(bind=True, max_retries=3)
def sync_job_task(self, routing_id: str):
    try:
        # Executa sync com retry
        result = await retry_handler.execute_with_retry(
            lambda: sync_use_case.execute(routing_uuid),
            max_retries=3,
            base_delay=2.0,
            operation_key=f"sync_job:{routing_id}"
        )
        
        return {"status": "success", "external_id": result.external_id}
        
    except Exception as e:
        # Retry com exponential backoff
        if self.request.retries < self.max_retries:
            retry_countdown = 60 * (2 ** self.request.retries)
            raise self.retry(countdown=retry_countdown)
        
        return {"status": "permanently_failed", "error": str(e)}
```

#### **Fase 5: Provider Integration**
```python
# Provider Manager com rate limiting
async def sync_job_routing(self, routing_id: UUID):
    # Check rate limiting
    rate_limit_key = f"sync:{company.id}:{company.provider_type.value}"
    
    if not await self.rate_limiter.check_and_increment(
        rate_limit_key, 
        max_requests=50,  # 50 syncs per minute
        window_seconds=60
    ):
        return False
    
    # Execute sync with retry logic
    result = await self.retry_handler.execute_with_retry(
        lambda: self.sync_use_case.execute(routing_id),
        max_retries=3,
        base_delay=2.0,
        operation_key=f"sync_job:{routing_id}"
    )
    
    return result
```

### **SLA Compliance & Performance**

#### **5-Minute SLA Guarantee**
- **Outbox Processing**: 30 segundos (máximo)
- **Celery Enqueueing**: 1 segundo (máximo)
- **Provider Sync**: 1-2 segundos (máximo)
- **Total**: ~32 segundos (dentro do SLA de 5 minutos)

#### **Performance Metrics**
- **Throughput**: 100+ jobs/minuto
- **Latency**: P95 < 2 segundos
- **Error Rate**: < 1%
- **Recovery Time**: < 30 segundos

### **Monitoring & Observability**

#### **Prometheus Metrics**
```python
# Job sync metrics
JOBS_SYNCED = Counter(
    'jobs_synced_total',
    'Total number of jobs synced to providers',
    ['provider_type', 'company_id', 'status']
)

JOB_SYNC_DURATION = Histogram(
    'job_sync_duration_seconds',
    'Time spent syncing jobs to providers',
    ['provider_type', 'company_id']
)

# Worker metrics
WORKER_TASKS_PROCESSED = Counter(
    'worker_tasks_processed_total',
    'Total number of tasks processed by workers',
    ['worker_type', 'task_type', 'status']
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Current state of circuit breakers',
    ['operation_type', 'component']
)
```

#### **Health Checks**
```bash
# Basic health check
GET /health/

# Readiness check (Kubernetes)
GET /health/ready

# Liveness check (Kubernetes)
GET /health/live

# Detailed health check
GET /health/detailed

# Prometheus metrics
GET /health/metrics
```

#### **Admin Endpoints**
```bash
# Worker status
GET /admin/workers/status

# Worker statistics
GET /admin/workers/stats

# Start all workers
POST /admin/workers/start

# Stop all workers
POST /admin/workers/stop

# Restart specific worker
POST /admin/workers/{worker_name}/restart

# System health
GET /admin/system/health

# System metrics
GET /admin/system/metrics
```

### **Error Handling & Recovery**

#### **Retry Strategy**
- **Exponential Backoff**: 1min, 2min, 4min
- **Jitter**: ±25% variação para evitar thundering herd
- **Max Retries**: 3 tentativas por padrão
- **Circuit Breaker**: Abre após 5 falhas consecutivas

#### **Error Types & Handling**
```python
# Provider errors
ProviderAPIError: Retry with backoff
ProviderConfigurationError: No retry, log for admin
ProviderRateLimitError: Retry after delay

# System errors
DatabaseConnectionError: Retry with backoff
NetworkTimeoutError: Retry with backoff
ValidationError: No retry, log for admin
```

#### **Recovery Mechanisms**
- **Automatic Retry**: Celery tasks com retry automático
- **Manual Retry**: Admin endpoints para retry manual
- **Circuit Breaker**: Previne sobrecarga de providers falhando
- **Graceful Degradation**: Sistema continua funcionando com funcionalidade reduzida

### **Configuration & Deployment**

#### **Environment Variables**
```bash
# Redis configuration
REDIS_URL=redis://localhost:6379/0

# Celery configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Worker configuration
WORKER_CONCURRENCY=4
WORKER_MAX_TASKS_PER_CHILD=1000

# Rate limiting
RATE_LIMIT_MAX_REQUESTS=50
RATE_LIMIT_WINDOW_SECONDS=60

# Retry configuration
MAX_RETRIES=3
BASE_RETRY_DELAY=2.0
```

#### **Docker Compose**
```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: .
    command: celery -A src.background.celery_app worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  celery-beat:
    build: .
    command: celery -A src.background.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
```

### **Testing & Development**

#### **Running Workers Locally**
```bash
# Start outbox worker
poetry run python -m src.background.workers.outbox_worker

# Start sync worker
poetry run python -m src.background.workers.sync_worker

# Start poll worker
poetry run python -m src.background.workers.poll_worker

# Start all workers
poetry run python -m src.background.workers
```

#### **Celery Commands**
```bash
# Start Celery worker
poetry run celery -A src.background.celery_app worker --loglevel=info

# Start Celery beat scheduler
poetry run celery -A src.background.celery_app beat --loglevel=info

# Monitor Celery
poetry run celery -A src.background.celery_app flower

# Inspect workers
poetry run celery -A src.background.celery_app inspect active
```

---

## 🎯 **Próximos Passos**

O **Job Sync Flow** está completamente implementado e funcionando! Agora podemos implementar:

1. **Status Polling Flow** - Verificação de updates dos providers
2. **Retry & Error Handling Flow** - Lógica avançada de retry
3. **Monitoring & Metrics Flow** - Dashboards e alertas
4. **Provider Integration Flow** - Novos providers (ServiceTitan, etc.)

**Qual fluxo você gostaria que eu implemente agora?** 🚀


