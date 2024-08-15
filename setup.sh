#!/bin/bash

# 🚀 Enterprise GenAI Platform Setup Script
# This script sets up the complete Enterprise GenAI Platform

echo "🚀 Setting up Enterprise GenAI Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your OpenAI API key and other settings"
fi

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check API health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API service is healthy"
else
    echo "❌ API service is not responding"
fi

# Check Prometheus
if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "✅ Prometheus is healthy"
else
    echo "❌ Prometheus is not responding"
fi

# Check Grafana
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Grafana is healthy"
else
    echo "❌ Grafana is not responding"
fi

echo ""
echo "🎉 Enterprise GenAI Platform is ready!"
echo ""
echo "📊 Access Points:"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Grafana Dashboards: http://localhost:3000 (admin/admin)"
echo "  • Prometheus Metrics: http://localhost:9090"
echo ""
echo "🚀 Quick Start:"
echo "  • Test API: curl http://localhost:8000/health"
echo "  • Execute workflow: See docs/getting-started.md"
echo ""
echo "📚 Documentation:"
echo "  • Getting Started: docs/getting-started.md"
echo "  • Workflow Config: docs/workflow-configuration.md"
echo "  • Agent Development: docs/agent-development.md"
echo ""
echo "🛠️ Development:"
echo "  • Install Python deps: pip install -r requirements.txt"
echo "  • Run tests: pytest tests/unit/"
echo "  • Run evaluations: pytest tests/evals/"
echo ""
echo "Happy coding! 🚀"
