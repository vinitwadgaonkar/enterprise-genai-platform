# Workflow Configuration Guide

This guide explains how to configure workflows using YAML configuration files.

## Workflow Structure

A workflow configuration consists of:

- **Metadata**: Name, description, version
- **Workflow Type**: RAG chain, tool calling, conversational, sequential
- **Steps**: Individual workflow steps
- **Prompts**: System and user prompt templates
- **Tools**: Available tools for the workflow
- **Memory**: Memory configuration
- **Token Budget**: Token usage limits

## Basic Workflow Example

```yaml
name: document_qa
description: Document Q&A with RAG
version: 1.0.0
workflow_type: rag_chain
steps:
  - name: retrieve
    type: retrieval
    config:
      vector_store: pgvector
      top_k: 5
      rerank: true
  
  - name: generate
    type: llm_call
    config:
      model: gpt-4
      temperature: 0.1
      max_tokens: 1000

prompts:
  system: "system/document_qa_system.j2"
  user: "user/document_qa_user.j2"

tools:
  - name: sql_tool
    enabled: true
  - name: api_tool
    enabled: false

memory:
  type: conversation_buffer
  max_tokens: 2000

token_budget: 10000
max_retries: 3
timeout_seconds: 300
```

## Workflow Types

### RAG Chain

Retrieval-Augmented Generation workflows:

```yaml
workflow_type: rag_chain
steps:
  - name: retrieve
    type: retrieval
    config:
      vector_store: pgvector
      top_k: 5
      similarity_threshold: 0.7
  
  - name: rerank
    type: rerank
    config:
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
      top_k: 3
  
  - name: generate
    type: llm_call
    config:
      model: gpt-4
      temperature: 0.1
```

### Tool Calling

Workflows with tool access:

```yaml
workflow_type: tool_calling
steps:
  - name: analyze_request
    type: llm_call
    config:
      model: gpt-4
      temperature: 0.1
  
  - name: execute_tools
    type: tool_call
    config:
      tools: [sql_tool, api_tool]
      max_iterations: 3
  
  - name: synthesize_response
    type: llm_call
    config:
      model: gpt-4
      temperature: 0.1
```

### Sequential

Step-by-step execution:

```yaml
workflow_type: sequential
steps:
  - name: step1
    type: llm_call
    config:
      model: gpt-4
  
  - name: step2
    type: tool_call
    config:
      tool: sql_tool
  
  - name: step3
    type: llm_call
    config:
      model: gpt-4
```

## Step Types

### Retrieval Steps

```yaml
- name: retrieve
  type: retrieval
  config:
    vector_store: pgvector  # or faiss
    top_k: 5
    similarity_threshold: 0.7
    filter_metadata:
      document_type: "technical"
    rerank: true
    rerank_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
```

### LLM Call Steps

```yaml
- name: generate
  type: llm_call
  config:
    model: gpt-4
    temperature: 0.1
    max_tokens: 1000
    top_p: 0.9
    frequency_penalty: 0.0
    presence_penalty: 0.0
```

### Tool Call Steps

```yaml
- name: execute_tool
  type: tool_call
  config:
    tool_name: sql_tool
    params:
      query: "SELECT * FROM users LIMIT 10"
    timeout_seconds: 30
    retry_count: 3
```

### Conditional Steps

```yaml
- name: conditional_step
  type: llm_call
  condition: "{{ previous_step.result.confidence > 0.8 }}"
  config:
    model: gpt-4
```

## Prompt Templates

### System Prompts

Create `prompts/system/document_qa_system.j2`:

```jinja2
You are a helpful document Q&A assistant.

## Instructions:
- Answer questions based on the provided context
- If the answer is not in the context, clearly state that
- Provide specific citations when possible
- Be concise but comprehensive

## Context:
{% if context %}
{% for doc in context %}
**Document {{ loop.index }}:**
{{ doc.content }}

{% if doc.metadata %}
Metadata: {{ doc.metadata | tojson }}
{% endif %}
---
{% endfor %}
{% endif %}

## Question:
{{ question }}
```

### User Prompts

Create `prompts/user/document_qa_user.j2`:

```jinja2
Based on the provided context documents, please answer the following question:

**Question:** {{ question }}

{% if additional_context %}
**Additional Context:** {{ additional_context }}
{% endif %}

Please provide a comprehensive answer with specific references to the source documents when possible.
```

### Critique Prompts

Create `prompts/critique/hallucination_detection.j2`:

```jinja2
You are a fact-checking assistant that evaluates AI responses for potential hallucinations.

## Your Task:
Analyze the following AI response for:
1. **Factual Accuracy**: Are the claims supported by the provided context?
2. **Hallucinations**: Does the response contain information not present in the context?
3. **Confidence Level**: How certain should we be about the response's accuracy?

## Context Provided:
{% if context %}
{% for doc in context %}
**Source {{ loop.index }}:**
{{ doc.content }}
---
{% endfor %}
{% endif %}

## AI Response to Evaluate:
{{ ai_response }}

Please provide a structured evaluation of the AI response.
```

## Memory Configuration

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

## Token Budgeting

### Global Token Budget

```yaml
token_budget: 10000  # Total tokens for the entire workflow
```

### Step-level Token Budget

```yaml
steps:
  - name: generate
    type: llm_call
    config:
      model: gpt-4
      max_tokens: 1000  # Tokens for this step
```

### Smart Truncation

```yaml
token_budget: 10000
truncation_strategy: "smart"  # or "simple"
max_context_tokens: 8000
```

## Error Handling

### Retry Configuration

```yaml
max_retries: 3
retry_delay: 1  # seconds
retry_backoff: 2  # exponential backoff multiplier
```

### Timeout Configuration

```yaml
timeout_seconds: 300  # Global timeout
steps:
  - name: slow_step
    type: tool_call
    timeout_seconds: 60  # Step-specific timeout
```

### Fallback Steps

```yaml
steps:
  - name: primary_step
    type: llm_call
    config:
      model: gpt-4
  
  - name: fallback_step
    type: llm_call
    condition: "{{ primary_step.status == 'failed' }}"
    config:
      model: gpt-3.5-turbo
```

## Environment Variables

Use environment variables in configurations:

```yaml
database_url: "${DATABASE_URL}"
api_key: "${OPENAI_API_KEY}"
model: "${DEFAULT_MODEL:gpt-4}"
```

## Validation

### Schema Validation

The platform validates workflow configurations against a JSON schema:

- Required fields must be present
- Field types must match expected types
- Step configurations must be valid
- Prompt templates must exist

### Runtime Validation

- Tool availability is checked at runtime
- Prompt templates are validated before execution
- Memory configurations are validated
- Token budgets are enforced

## Best Practices

### 1. Keep Workflows Simple

- Use clear, descriptive step names
- Limit the number of steps
- Avoid complex conditional logic

### 2. Use Appropriate Models

- Use GPT-4 for complex reasoning
- Use GPT-3.5-turbo for simple tasks
- Consider token costs

### 3. Optimize Token Usage

- Set appropriate token budgets
- Use smart truncation
- Monitor token usage

### 4. Handle Errors Gracefully

- Set reasonable timeouts
- Use fallback steps
- Provide meaningful error messages

### 5. Test Thoroughly

- Use the evaluation framework
- Test with various inputs
- Monitor performance metrics

## Examples

### Document Q&A Workflow

```yaml
name: document_qa
description: Answer questions about documents
version: 1.0.0
workflow_type: rag_chain
steps:
  - name: retrieve
    type: retrieval
    config:
      vector_store: pgvector
      top_k: 5
      similarity_threshold: 0.7
  
  - name: rerank
    type: rerank
    config:
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
      top_k: 3
  
  - name: generate
    type: llm_call
    config:
      model: gpt-4
      temperature: 0.1
      max_tokens: 1000

prompts:
  system: "system/document_qa_system.j2"
  user: "user/document_qa_user.j2"

memory:
  type: conversation_buffer
  max_tokens: 2000

token_budget: 10000
max_retries: 3
timeout_seconds: 300
```

### SQL Analyst Agent

```yaml
name: sql_analyst
description: SQL query analyst with tool access
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
token_budget: 15000
```

This configuration guide provides everything you need to create powerful, efficient workflows for your GenAI applications.
