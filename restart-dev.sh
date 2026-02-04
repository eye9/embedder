#!/bin/bash
# Quick restart script for development environment

echo "🔄 Restarting development environment..."
echo ""

# Stop containers
echo "⏹️  Stopping containers..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Clear Redis cache (optional)
echo "🗑️  Clearing Redis cache..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d redis
sleep 2
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T redis redis-cli FLUSHALL
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Start containers with build
echo "🚀 Starting containers with fresh build..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Show status
echo ""
echo "📊 Container status:"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

echo ""
echo "✅ Development environment restarted!"
echo ""
echo "📝 Useful commands:"
echo "  View logs:        docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f"
echo "  View worker logs: docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker"
echo "  Restart worker:   docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker"
echo "  Stop all:         docker-compose -f docker-compose.yml -f docker-compose.dev.yml down"
echo ""
echo "🌐 Web interface: http://localhost:8000"
echo "🔑 Login: admin / admin123"