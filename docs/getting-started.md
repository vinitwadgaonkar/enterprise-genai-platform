# Getting Started with Enterprise GenAI Platform

This guide will help you get up and running with the Enterprise GenAI Platform in under 10 minutes.

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- OpenAI API key

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd enterprise-genai-platform
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Database settings (defaults work for Docker)
DATABASE_URL=postgresql://genai:password@localhost:5432/genai_platform
REDIS_URL=redis://localhost:6379/0
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check Prometheus metrics
curl http://localhost:9090/metrics

# Check Grafana (admin/admin)
open http://localhost:3000
```

## Your First Workflow

### 1. Create a Simple Workflow

Create `config/workflows/hello_world.yaml`:

```yaml
name: hello_world
description: A simple hello world workflow
version: 1.0.0
workflow_type: rag_chain
steps:
  - name: generate_response
    type: llm_call
    config:
      model: gpt-4
      temperature: 0.1
      max_tokens: 100
prompts:
  system: "system/hello_world_system.j2"
  user: "user/hello_world_user.j2"
```

### 2. Create Prompt Templates

Create `prompts/system/hello_world_system.j2`:

```jinja2
You are a helpful assistant that greets users warmly.
```

Create `prompts/user/hello_world_user.j2`:

```jinja2
User says: {{ user_input }}
Please respond with a friendly greeting.
```

### 3. Execute the Workflow

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "workflow_id": "hello_world",
       "input_data": {
         "user_input": "Hello, how are you?"
       }
     }'
```

## Your First Agent

### 1. Create an Agent Configuration

Create `config/agents/helpful_assistant.yaml`:

```yaml
name: helpful_assistant
description: A helpful assistant with tool access
version: 1.0.0
agent_type: tool_calling
model: gpt-4
temperature: 0.1
tools:
  - sql_tool
  - api_tool
prompts:
  system: "system/helpful_assistant_system.j2"
```

### 2. Execute the Agent

```bash
curl -X POST "http://localhost:8000/api/v1/agents/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "helpful_assistant",
       "input_data": {
         "query": "Can you help me analyze some data?"
       }
     }'
```

## Monitoring and Observability

### Grafana Dashboards

Access Grafana at http://localhost:3000 (admin/admin) to view:

- **Overview Dashboard**: Request rates, response times, error rates
- **LLM Metrics**: Token usage, costs, model performance
- **Vector Store Metrics**: Search performance, index statistics
- **Tool Metrics**: Execution times, success rates

### Prometheus Metrics

Access Prometheus at http://localhost:9090 to explore metrics:

- `genai_requests_total`: Total API requests
- `genai_llm_tokens_total`: LLM token usage
- `genai_workflow_executions_total`: Workflow execution counts
- `genai_tool_executions_total`: Tool execution counts

### Logs

View structured logs:

```bash
# API logs
docker-compose logs -f api

# All services
docker-compose logs -f
```

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/unit/

# Run evaluations
pytest tests/evals/

# Start API locally
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Workflows

1. Create YAML config in `config/workflows/`
2. Add prompt templates in `prompts/`
3. Test with evaluation suite
4. Deploy via CI/CD pipeline

### Adding New Tools

1. Create tool class in `src/tools/`
2. Register with tool registry
3. Add to agent configurations
4. Test with unit tests

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart
```

**Database connection issues:**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
```

**API errors:**
```bash
# Check API logs
docker-compose logs api

# Test API directly
curl http://localhost:8000/health
```

### Performance Tuning

- **Memory**: Increase Docker memory limits
- **Database**: Tune PostgreSQL settings
- **Vector Store**: Optimize Faiss index parameters
- **LLM**: Adjust token budgets and model settings

## Next Steps

- [Workflow Configuration Guide](workflow-configuration.md)
- [Agent Development Guide](agent-development.md)
- [Prompt Template Library](prompt-templates.md)
- [Evaluation Framework](evaluation-framework.md)
- [Deployment Guide](deployment.md)
