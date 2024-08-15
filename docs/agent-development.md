# Agent Development Guide

This guide explains how to develop and configure AI agents using the Enterprise GenAI Platform.

## Agent Types

The platform supports several agent types:

- **Tool Calling**: Agents that can use tools (SQL, API, etc.)
- **Conversational**: Chat-based agents with memory
- **ReAct**: Reasoning and Acting agents

## Basic Agent Configuration

```yaml
name: helpful_assistant
description: A helpful assistant with tool access
version: 1.0.0
agent_type: tool_calling
model: gpt-4
temperature: 0.1
max_tokens: 1000
tools:
  - sql_tool
  - api_tool
prompts:
  system: "system/helpful_assistant_system.j2"
  user: "user/helpful_assistant_user.j2"
memory:
  type: conversation_buffer
  max_tokens: 2000
token_budget: 15000
```

## Tool Calling Agents

### Configuration

```yaml
name: sql_analyst
description: SQL query analyst
version: 1.0.0
agent_type: tool_calling
model: gpt-4
temperature: 0.1
tools:
  - sql_tool
  - api_tool
prompts:
  system: "system/sql_analyst_system.j2"
  user: "user/sql_analyst_user.j2"
memory:
  type: conversation_buffer
  max_tokens: 2000
```

### System Prompt

Create `prompts/system/sql_analyst_system.j2`:

```jinja2
You are an expert SQL analyst with access to database tools.

## Capabilities:
- Execute SQL queries safely
- Analyze query results and provide insights
- Suggest optimizations for queries
- Explain complex SQL concepts
- Generate reports and visualizations

## Safety Guidelines:
- Always validate queries before execution
- Never execute DROP, DELETE, or other destructive operations
- Limit result sets to reasonable sizes
- Use parameterized queries when possible

## Database Schema:
{% if schema_info %}
{{ schema_info }}
{% endif %}

## Instructions:
- Understand the user's data requirements
- Write safe, efficient SQL queries
- Execute queries and analyze results
- Provide clear explanations and insights
- Suggest follow-up analyses when appropriate

You have access to the following tools:
- SQL execution tool for running queries
- Query result analysis and formatting
- Data visualization suggestions
```

### User Prompt

Create `prompts/user/sql_analyst_user.j2`:

```jinja2
User Request: {{ user_input }}

{% if previous_context %}
Previous Context: {{ previous_context }}
{% endif %}

{% if database_schema %}
Available Tables:
{% for table, columns in database_schema.items() %}
- {{ table }}: {{ columns | join(', ') }}
{% endfor %}
{% endif %}

Please help the user with their SQL analysis request.
```

## Conversational Agents

### Configuration

```yaml
name: chat_assistant
description: General purpose chat assistant
version: 1.0.0
agent_type: conversational
model: gpt-4
temperature: 0.7
max_tokens: 500
prompts:
  system: "system/chat_assistant_system.j2"
  user: "user/chat_assistant_user.j2"
memory:
  type: conversation_buffer
  max_tokens: 2000
```

### System Prompt

Create `prompts/system/chat_assistant_system.j2`:

```jinja2
You are a helpful, harmless, and honest assistant.

## Your Role:
- Provide helpful and accurate information
- Be conversational and engaging
- Admit when you don't know something
- Ask clarifying questions when needed

## Guidelines:
- Be concise but comprehensive
- Use examples when helpful
- Maintain a friendly tone
- Respect user privacy and boundaries

## Memory:
You have access to conversation history to provide context-aware responses.
```

## ReAct Agents

### Configuration

```yaml
name: research_assistant
description: Research assistant with reasoning and acting
version: 1.0.0
agent_type: react
model: gpt-4
temperature: 0.1
tools:
  - api_tool
  - sql_tool
prompts:
  system: "system/research_assistant_system.j2"
  user: "user/research_assistant_user.j2"
memory:
  type: conversation_buffer
  max_tokens: 2000
```

### System Prompt

Create `prompts/system/research_assistant_system.j2`:

```jinja2
You are a research assistant that uses reasoning and acting to solve problems.

## ReAct Framework:
1. **Reason**: Think about the problem and what information you need
2. **Act**: Use available tools to gather information
3. **Observe**: Analyze the results and determine next steps
4. **Repeat**: Continue until you have enough information to answer

## Available Tools:
- API tool for external data
- SQL tool for database queries
- Web search capabilities

## Instructions:
- Break down complex problems into steps
- Use tools systematically to gather information
- Synthesize findings into clear answers
- Explain your reasoning process
```

## Memory Management

### Conversation Buffer

```yaml
memory:
  type: conversation_buffer
  max_tokens: 2000
  return_messages: true
```

### Summary Memory

```yaml
memory:
  type: summary
  max_token_limit: 1000
  return_messages: true
```

### Entity Memory

```yaml
memory:
  type: entity
  return_messages: true
```

### Combined Memory

```yaml
memory:
  type: combined
  memories:
    - type: conversation_buffer
      max_tokens: 1000
    - type: summary
      max_token_limit: 500
    - type: entity
```

## Tool Integration

### Available Tools

- **SQL Tool**: Execute database queries
- **API Tool**: Make HTTP requests
- **Custom Tools**: Add your own tools

### Tool Configuration

```yaml
tools:
  - name: sql_tool
    config:
      connection_string: "${DATABASE_URL}"
      max_rows: 100
      timeout_seconds: 30
  
  - name: api_tool
    config:
      base_url: "https://api.example.com"
      timeout_seconds: 30
      rate_limit_per_minute: 60
```

### Custom Tools

Create custom tools by extending the base tool class:

```python
from src.tools.base import BaseTool, ToolResult

class CustomTool(BaseTool):
    def __init__(self, **kwargs):
        super().__init__(
            name="custom_tool",
            description="A custom tool",
            **kwargs
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        # Tool implementation
        return ToolResult(
            success=True,
            data={"result": "Custom tool executed"},
            metadata={"tool": "custom_tool"}
        )
    
    def get_schema(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        }
```

## Agent Execution

### API Execution

```bash
curl -X POST "http://localhost:8000/api/v1/agents/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "sql_analyst",
       "input_data": {
         "query": "Show me the top 5 customers by revenue"
       }
     }'
```

### Python Execution

```python
from src.core.workflow_engine import WorkflowEngine

# Initialize engine
engine = WorkflowEngine(openai_api_key="your-key")

# Execute agent
result = await engine.execute_agent(
    agent_id="sql_analyst",
    input_data={"query": "Analyze customer data"}
)

print(f"Status: {result.status}")
print(f"Output: {result.output}")
```

## Testing Agents

### Unit Tests

```python
import pytest
from src.core.workflow_engine import WorkflowEngine

@pytest.mark.asyncio
async def test_sql_analyst():
    engine = WorkflowEngine(openai_api_key="test-key")
    
    result = await engine.execute_agent(
        agent_id="sql_analyst",
        input_data={"query": "Show me all users"}
    )
    
    assert result.status == "completed"
    assert "sql" in result.output.lower()
```

### Evaluation Tests

Create `tests/evals/agent_tests.json`:

```json
{
  "tests": [
    {
      "test_id": "sql_analyst_001",
      "test_type": "agent",
      "input_data": {
        "query": "Show me the top 5 customers by revenue"
      },
      "expected_output": {
        "sql_query": "SELECT c.name, SUM(o.amount) as revenue FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.name ORDER BY revenue DESC LIMIT 5"
      },
      "metadata": {
        "agent_id": "sql_analyst"
      }
    }
  ]
}
```

## Best Practices

### 1. Clear Agent Purpose

- Define the agent's specific role
- Use descriptive names and descriptions
- Set appropriate temperature and token limits

### 2. Effective Prompts

- Write clear, specific system prompts
- Include examples and guidelines
- Use Jinja2 templating for flexibility

### 3. Tool Selection

- Choose tools that match the agent's purpose
- Configure tools appropriately
- Test tool integrations

### 4. Memory Management

- Use appropriate memory types
- Set reasonable token limits
- Monitor memory usage

### 5. Error Handling

- Set appropriate timeouts
- Use retry logic
- Provide fallback responses

### 6. Testing

- Write comprehensive tests
- Use evaluation frameworks
- Monitor performance metrics

## Monitoring and Observability

### Metrics

- Agent execution times
- Tool usage patterns
- Memory usage
- Error rates

### Logs

- Structured logging with correlation IDs
- Agent decision traces
- Tool execution logs

### Dashboards

- Grafana dashboards for agent performance
- Prometheus metrics for monitoring
- Alerting for anomalies

## Examples

### Customer Service Agent

```yaml
name: customer_service
description: Customer service agent with knowledge base access
version: 1.0.0
agent_type: tool_calling
model: gpt-4
temperature: 0.3
tools:
  - knowledge_base_tool
  - ticket_system_tool
prompts:
  system: "system/customer_service_system.j2"
  user: "user/customer_service_user.j2"
memory:
  type: conversation_buffer
  max_tokens: 2000
```

### Data Analyst Agent

```yaml
name: data_analyst
description: Data analysis agent with SQL and visualization tools
version: 1.0.0
agent_type: tool_calling
model: gpt-4
temperature: 0.1
tools:
  - sql_tool
  - visualization_tool
  - api_tool
prompts:
  system: "system/data_analyst_system.j2"
  user: "user/data_analyst_user.j2"
memory:
  type: conversation_buffer
  max_tokens: 3000
```

This guide provides everything you need to develop powerful, efficient AI agents for your applications.
