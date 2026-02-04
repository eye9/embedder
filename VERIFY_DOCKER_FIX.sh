#!/bin/bash
# Verification script for Docker color coding fix

echo "🔍 Verifying color coding fix in Docker..."
echo ""

# Check if containers are running
echo "1️⃣ Checking if containers are running..."
if ! docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "❌ Containers are not running!"
    echo "   Run: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d"
    exit 1
fi
echo "✅ Containers are running"
echo ""

# Check if code is mounted
echo "2️⃣ Checking if code is mounted as volume..."
if docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker test -f /app/batch_processor/workers/processing_task.py; then
    echo "✅ Code is accessible in worker container"
else
    echo "❌ Code is not accessible in worker container!"
    exit 1
fi
echo ""

# Check if confidence_score is in the code
echo "3️⃣ Checking if confidence_score fix is present..."
if docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker grep -q "'confidence_score': result.confidence_score" /app/batch_processor/workers/processing_task.py; then
    echo "✅ confidence_score fix is present in the code"
    echo ""
    echo "   Found at line:"
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker grep -n "'confidence_score': result.confidence_score" /app/batch_processor/workers/processing_task.py
else
    echo "❌ confidence_score fix is NOT present in the code!"
    echo "   Expected to find: 'confidence_score': result.confidence_score"
    exit 1
fi
echo ""

# Check if openpyxl is installed
echo "4️⃣ Checking if openpyxl is installed..."
if docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker python -c "from openpyxl.styles import PatternFill; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo "✅ openpyxl is installed and working"
else
    echo "❌ openpyxl is not installed or not working!"
    exit 1
fi
echo ""

# Check web service health
echo "5️⃣ Checking web service health..."
if curl -s http://localhost:8000/health | grep -q "ok"; then
    echo "✅ Web service is healthy"
else
    echo "⚠️  Web service health check failed (might be starting up)"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All checks passed!"
echo ""
echo "📝 Next steps:"
echo "   1. Open http://localhost:8000"
echo "   2. Login: admin / admin123"
echo "   3. Upload test_web_color_coding.xlsx"
echo "   4. Download result and check colors in Excel"
echo ""
echo "📊 View logs:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker"
echo ""
echo "🔄 Restart worker if needed:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"