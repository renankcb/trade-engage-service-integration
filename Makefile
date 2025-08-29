# Makefile for ServiceTitan Integration Service
# Provides convenient commands for development, deployment, and maintenance

.PHONY: help install setup build up down logs clean test migrate seed lint format check
.DEFAULT_GOAL := help

# Variables
COMPOSE_FILE := docker-compose.yml
SERVICE_NAME := servicetitan-integration
PYTHON := poetry run python
POETRY := poetry

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
help:
	@echo "TradeEngage Service Integration - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install dependencies with Poetry"
	@echo "  test        - Run tests"
	@echo "  run         - Run the application"
	@echo ""
	@echo "Redis Management:"
	@echo "  redis-flush - Clear all Redis data (FLUSHALL)"
	@echo "  redis-clear - Clear only Celery queues and results"
	@echo "  redis-info  - Show Redis info and memory usage"
	@echo "  redis-monitor - Monitor Redis commands in real-time"
	@echo ""
	@echo "Docker Management:"
	@echo "  docker-up   - Start all services"
	@echo "  docker-down - Stop all services"
	@echo "  docker-restart - Restart all services"
	@echo "  docker-restart-workers - Restart specific Celery workers"
	@echo "  docker-logs - Show logs from all services"
	@echo "  docker-logs-workers - Show logs from specific Celery workers"
	@echo ""
	@echo "Celery Management:"
	@echo "  celery-status - Show Celery worker status"
	@echo "  celery-purge - Purge all Celery queues"
	@echo "  celery-monitor - Monitor Celery tasks in real-time"
	@echo ""
	@echo "Task Queue Management:"
	@echo "  celery-clear-queues      - Clear all Celery queues"
	@echo "  celery-clear-default-queue - Clear default queue (sync_job_task)"
	@echo "  celery-clear-sync-queue    - Clear sync queue"
	@echo "  celery-clear-all-queues    - Clear all specific queues"
	@echo "  celery-list-queues         - List all queues and contents"
	@echo "  celery-list-tasks          - List all registered tasks"
	@echo "  celery-cancel-all          - Cancel all running tasks"
	@echo "  celery-cancel-by-queue     - Cancel tasks in specific queue (QUEUE=name)"
	@echo ""
	@echo "Quick cleanup command:"
	@echo "  clean       - Clean up Celery queues and Redis data"

# Development Setup
install: ## Install Python dependencies
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	$(POETRY) install
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

setup: ## Complete development environment setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh
	@echo "$(GREEN)✅ Development environment ready!$(NC)"

# Docker Commands
build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose -f $(COMPOSE_FILE) build --no-cache
	@echo "$(GREEN)✅ Docker images built$(NC)"

up: ## Start all services
	@echo "$(BLUE)Starting all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)✅ All services started$(NC)"
	@echo "$(YELLOW)Services available at:$(NC)"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - Grafana: http://localhost:3000"
	@echo "  - Prometheus: http://localhost:9091"

down: ## Stop all services
	@echo "$(BLUE)Stopping all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✅ All services stopped$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting all services...$(NC)"
	@$(MAKE) down
	@$(MAKE) up

logs: ## Show logs for all services
	@echo "$(BLUE)Showing logs for all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api: ## Show API service logs
	@echo "$(BLUE)Showing API service logs...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f api

logs-worker: ## Show worker service logs
	@echo "$(BLUE)Showing worker service logs...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f worker

logs-scheduler: ## Show scheduler service logs
	@echo "$(BLUE)Showing scheduler service logs...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f scheduler

# Database Commands
db-up: ## Start database services only
	@echo "$(BLUE)Starting database services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d postgres redis
	@echo "$(GREEN)✅ Database services started$(NC)"

db-down: ## Stop database services
	@echo "$(BLUE)Stopping database services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) stop postgres redis
	@echo "$(GREEN)✅ Database services stopped$(NC)"

db-reset: ## Reset database (drop and recreate)
	@echo "$(RED)⚠️  This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "$(BLUE)Resetting database...$(NC)"; \
		docker-compose -f $(COMPOSE_FILE) down postgres; \
		docker volume rm service-integration_postgres_data || true; \
		$(MAKE) db-up; \
		sleep 10; \
		$(MAKE) migrate; \
		$(MAKE) seed; \
		echo "$(GREEN)✅ Database reset complete$(NC)"; \
	else \
		echo ""; \
		echo "$(YELLOW)Database reset cancelled$(NC)"; \
	fi

db-shell: ## Connect to PostgreSQL shell
	@echo "$(BLUE)Connecting to PostgreSQL shell...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec postgres psql -U integration_user -d integration_service

db-backup: ## Create database backup
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	docker-compose -f $(COMPOSE_FILE) exec -T postgres pg_dump -U integration_user integration_service > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup created in backups/ directory$(NC)"

db-restore: ## Restore database from backup
	@echo "$(BLUE)Available backups:$(NC)"
	@ls -la backups/*.sql 2>/dev/null || echo "No backups found"
	@echo "$(YELLOW)Usage: make db-restore BACKUP_FILE=backups/filename.sql$(NC)"

# Migration Commands
migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(PYTHON) -m alembic upgrade head
	@echo "$(GREEN)✅ Migrations completed$(NC)"

migrate-create: ## Create a new migration file
	@echo "$(BLUE)Creating new migration...$(NC)"
	@read -p "Enter migration description: " desc; \
	$(PYTHON) -m alembic revision --autogenerate -m "$$desc"
	@echo "$(GREEN)✅ Migration created$(NC)"

migrate-downgrade: ## Downgrade to previous migration
	@echo "$(BLUE)Downgrading migration...$(NC)"
	$(PYTHON) -m alembic downgrade -1
	@echo "$(GREEN)✅ Migration downgraded$(NC)"

migrate-status: ## Show migration status
	@echo "$(BLUE)Migration status:$(NC)"
	$(PYTHON) -m alembic current
	@echo "$(GREEN)✅ Status shown$(NC)"

migrate-docker: ## Run migrations in Docker environment
	@echo "$(BLUE)Running migrations in Docker...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api $(PYTHON) -m alembic upgrade head
	@echo "$(GREEN)✅ Migrations completed$(NC)"

seed: ## Seed database with test data
	@echo "$(BLUE)Seeding database with test data...$(NC)"
	MIGRATION_DATABASE_URL="postgresql+asyncpg://integration_user:integration_pass@localhost:5432/integration_service" $(PYTHON) scripts/seed_data.py
	@echo "$(GREEN)✅ Database seeded$(NC)"

seed-docker: ## Seed database in Docker environment
	@echo "$(BLUE)Seeding database in Docker...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api $(PYTHON) scripts/seed_data.py
	@echo "$(GREEN)✅ Database seeded$(NC)"

# Application Commands
run: ## Run the API server locally
	@echo "$(BLUE)Starting API server...$(NC)"
	$(PYTHON) src/main.py

run-dev: ## Run the API server in development mode
	@echo "$(BLUE)Starting API server in development mode...$(NC)"
	$(PYTHON) -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

worker: ## Start Celery worker
	@echo "$(BLUE)Starting Celery worker...$(NC)"
	$(PYTHON) -m celery -A src.background.celery_app worker --loglevel=info --concurrency=2

worker-docker: ## Start Celery worker in Docker
	@echo "$(BLUE)Starting Celery worker in Docker...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d worker

scheduler: ## Start Celery beat scheduler
	@echo "$(BLUE)Starting Celery beat scheduler...$(NC)"
	$(PYTHON) -m celery -A src.background.celery_app beat --loglevel=info

scheduler-docker: ## Start Celery beat scheduler in Docker
	@echo "$(BLUE)Starting Celery beat scheduler in Docker...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d scheduler

# Testing Commands
test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	$(POETRY) run pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(POETRY) run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(POETRY) run pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	@echo "$(BLUE)Running end-to-end tests...$(NC)"
	$(POETRY) run pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(POETRY) run pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Code Quality Commands
lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	$(POETRY) run flake8 src/ tests/
	$(POETRY) run mypy src/
	@echo "$(GREEN)✅ Linting completed$(NC)"

format: ## Format code with Black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	$(POETRY) run black src/ tests/
	$(POETRY) run isort src/ tests/
	@echo "$(GREEN)✅ Code formatted$(NC)"

check: ## Run all code quality checks
	@echo "$(BLUE)Running code quality checks...$(NC)"
	@$(MAKE) format
	@$(MAKE) lint
	@$(MAKE) test
	@echo "$(GREEN)✅ All checks passed$(NC)"

# Monitoring Commands
monitor: ## Start monitoring services
	@echo "$(BLUE)Starting monitoring services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d prometheus grafana
	@echo "$(GREEN)✅ Monitoring services started$(NC)"
	@echo "$(YELLOW)Available at:$(NC)"
	@echo "  - Prometheus: http://localhost:9091"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"

health: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -s http://localhost:8000/api/v1/health | jq . || echo "$(RED)API not responding$(NC)"
	@curl -s http://localhost:8000/api/v1/health/ready | jq . || echo "$(RED)Readiness check failed$(NC)"

# Utility Commands
clean: ## Clean up Docker resources and temporary files
	@echo "$(BLUE)Cleaning up...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v
	docker system prune -f
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

status: ## Show status of all services
	@echo "$(BLUE)Service Status:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BLUE)Container Resources:$(NC)"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

shell: ## Open shell in API container
	@echo "$(BLUE)Opening shell in API container...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api /bin/bash

# Production Commands
deploy: ## Deploy production version
	@echo "$(BLUE)Deploying production version...$(NC)"
	docker build --target production -t $(SERVICE_NAME):latest .
	@echo "$(GREEN)✅ Production image built$(NC)"
	@echo "$(YELLOW)Run with: docker run -d --name $(SERVICE_NAME) -p 8000:8000 $(SERVICE_NAME):latest$(NC)"

# Development Workflow
dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	@$(MAKE) db-up
	@$(MAKE) migrate
	@$(MAKE) seed
	@$(MAKE) run-dev

dev-full: ## Start full development environment with all services
	@echo "$(BLUE)Starting full development environment...$(NC)"
	@$(MAKE) up
	@$(MAKE) worker-docker
	@$(MAKE) scheduler-docker
	@$(MAKE) monitor
	@echo "$(GREEN)✅ Full development environment ready!$(NC)"

# Quick Commands
quick: ## Quick start (database + API)
	@echo "$(BLUE)Quick start...$(NC)"
	@$(MAKE) db-up
	@$(MAKE) migrate
	@$(MAKE) run-dev

stop: ## Stop all services and cleanup
	@echo "$(BLUE)Stopping all services...$(NC)"
	@$(MAKE) down
	@echo "$(GREEN)✅ All services stopped$(NC)"

# Show available commands
list: ## List all available commands
	@echo "$(BLUE)Available commands:$(NC)"
	@$(MAKE) help

# Celery Management commands
celery-status:
	@echo "Celery Worker Status:"
	docker-compose exec worker celery -A src.background.celery_app:celery_app inspect stats

celery-purge:
	@echo "Purging all Celery queues..."
	docker-compose exec worker celery -A src.background.celery_app:celery_app purge -f

celery-monitor:
	@echo "Monitoring Celery tasks in real-time..."
	docker-compose exec worker celery -A src.background.celery_app:celery_app events

# Task Queue Management commands
celery-clear-queues:
	@echo "Clearing all Celery queues..."
	docker-compose exec worker celery -A src.background.celery_app:celery_app purge -f
	@echo "✅ All Celery queues cleared"

celery-clear-default-queue:
	@echo "Clearing default queue (sync_job_task)..."
	docker-compose exec worker celery -A src.background.celery_app:celery_app purge -Q default -f
	@echo "✅ Default queue cleared"

celery-clear-sync-queue:
	@echo "Clearing sync queue..."
	docker-compose exec worker celery -A src.background.celery_app:celery_app purge -Q sync -f
	@echo "✅ Sync queue cleared"

celery-clear-all-queues:
	@echo "Clearing all specific queues..."
	docker-compose exec worker celery -A src.background.celery_app:celery_app purge -Q default,sync,maintenance,poll,retry -f
	@echo "✅ All specific queues cleared"

celery-list-queues:
	@echo "Listing all Celery queues and their contents:"
	docker-compose exec worker celery -A src.background.celery_app:celery_app inspect active_queues

celery-list-tasks:
	@echo "Listing all registered Celery tasks:"
	docker-compose exec worker celery -A src.background.celery_app:celery_app inspect registered

celery-cancel-all:
	@echo "Cancelling all running Celery tasks..."
	docker-compose exec worker celery -A src.background.celery_app:celery_app control revoke --all
	@echo "✅ All running tasks cancelled"

celery-cancel-by-queue:
	@echo "Usage: make celery-cancel-by-queue QUEUE=default"
	@echo "Cancelling all tasks in specific queue..."
	@if [ -z "$(QUEUE)" ]; then \
		echo "❌ Please specify QUEUE parameter (e.g., make celery-cancel-by-queue QUEUE=default)"; \
		exit 1; \
	fi
	docker-compose exec worker celery -A src.background.celery_app:celery_app control revoke --queue=$(QUEUE) --all
	@echo "✅ All tasks in $(QUEUE) queue cancelled"
