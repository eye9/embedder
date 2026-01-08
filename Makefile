# Makefile for Batch Excel Processor Docker Management

.PHONY: help build up down logs clean dev prod test

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start services in production mode"
	@echo "  down      - Stop and remove containers"
	@echo "  logs      - Show logs from all services"
	@echo "  clean     - Remove containers, networks, and volumes"
	@echo "  dev       - Start services in development mode"
	@echo "  prod      - Start services in production mode"
	@echo "  test      - Run tests in Docker container"
	@echo "  shell     - Open shell in web container"
	@echo "  redis-cli - Open Redis CLI"
	@echo "  flower    - Start Flower monitoring"

# Build Docker images
build:
	docker-compose build

# Start services in production mode
up: build
	docker-compose up -d

# Start services in production mode (foreground)
up-fg: build
	docker-compose up

# Stop and remove containers
down:
	docker-compose down

# Show logs from all services
logs:
	docker-compose logs -f

# Remove containers, networks, and volumes
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Start services in development mode
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Start services in production mode
prod: up

# Run tests in Docker container
test:
	docker-compose run --rm web python -m pytest tests/ -v

# Open shell in web container
shell:
	docker-compose exec web bash

# Open Redis CLI
redis-cli:
	docker-compose exec redis redis-cli

# Start Flower monitoring
flower:
	docker-compose --profile monitoring up flower -d

# Check service status
status:
	docker-compose ps

# View service logs individually
logs-web:
	docker-compose logs -f web

logs-worker:
	docker-compose logs -f worker

logs-redis:
	docker-compose logs -f redis

# Restart specific services
restart-web:
	docker-compose restart web

restart-worker:
	docker-compose restart worker

restart-redis:
	docker-compose restart redis

# Scale workers
scale-workers:
	docker-compose up -d --scale worker=3

# Health check
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "Web service unhealthy"
	@docker-compose exec redis redis-cli ping || echo "Redis unhealthy"