# 🤝 Contributing to Enterprise GenAI Platform

Thank you for your interest in contributing to the Enterprise GenAI Platform! This document provides guidelines and information for contributors.

## 🚀 Quick Start for Contributors

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Git
- OpenAI API key (for testing)

### Setup Development Environment
```bash
# Clone the repository
git clone https://github.com/vinitwadgaonkar/enterprise-genai-platform.git
cd enterprise-genai-platform

# Install dependencies
pip install -r requirements.txt

# Start services
./setup.sh

# Run tests
pytest tests/unit/ -v
```

## 📋 Development Workflow

### 1. Fork and Clone
```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/your-username/enterprise-genai-platform.git
cd enterprise-genai-platform

# Add upstream remote
git remote add upstream https://github.com/vinitwadgaonkar/enterprise-genai-platform.git
```

### 2. Create Feature Branch
```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/bug-description
```

### 3. Make Changes
- Write clean, well-documented code
- Add tests for new functionality
- Update documentation as needed
- Follow the coding standards (see below)

### 4. Test Your Changes
```bash
# Run unit tests
pytest tests/unit/ -v --cov=src

# Run evaluation tests
pytest tests/evals/ -v

# Run linting
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

### 5. Commit Changes
```bash
git add .
git commit -m "feat: add amazing feature

- Implement new workflow type
- Add comprehensive tests
- Update documentation
- Fix related bugs"
```

### 6. Push and Create PR
```bash
git push origin feature/amazing-feature
# Create Pull Request on GitHub
```

## 🎯 Areas for Contribution

### 🧠 Core Platform
- **Workflow Engine**: Enhance workflow execution and error handling
- **Agent Framework**: Improve agent capabilities and tool integration
- **Configuration System**: Add new configuration options and validation
- **Memory Management**: Optimize memory usage and add new memory types

### 🔍 AI & ML Components
- **Retrieval Systems**: Improve vector search and reranking algorithms
- **Embedding Pipelines**: Optimize embedding generation and storage
- **Query Processing**: Enhance query rewriting and understanding
- **Evaluation Framework**: Add new evaluation metrics and tests

### 🛠️ Tools & Integrations
- **New Tools**: Add SQL, API, or custom tools
- **Tool Registry**: Improve tool discovery and management
- **Authentication**: Add OAuth, JWT, or other auth methods
- **Rate Limiting**: Enhance rate limiting and throttling

### 📊 Observability
- **Metrics**: Add new Prometheus metrics
- **Dashboards**: Create Grafana dashboards
- **Tracing**: Enhance OpenTelemetry instrumentation
- **Logging**: Improve structured logging and correlation

### 🧪 Testing & Quality
- **Unit Tests**: Add comprehensive test coverage
- **Integration Tests**: Test API endpoints and workflows
- **Evaluation Tests**: Add golden-answer test cases
- **Performance Tests**: Benchmark and optimize performance

### 📚 Documentation
- **API Documentation**: Improve FastAPI docs
- **User Guides**: Create tutorials and examples
- **Architecture Docs**: Document system design
- **Deployment Guides**: Add cloud deployment instructions

## 🎨 Coding Standards

### Python Code Style
```python
# Use type hints
def process_workflow(workflow_id: str, input_data: Dict[str, Any]) -> ExecutionResult:
    """Process a workflow with given input data.
    
    Args:
        workflow_id: Unique identifier for the workflow
        input_data: Input data for the workflow
        
    Returns:
        ExecutionResult: Result of workflow execution
        
    Raises:
        WorkflowNotFoundError: If workflow doesn't exist
        ValidationError: If input data is invalid
    """
    # Implementation
```

### Documentation Standards
```python
class WorkflowEngine:
    """Orchestrates workflow execution based on YAML configurations.
    
    The WorkflowEngine is the core component that executes workflows
    and agents defined in YAML configuration files. It handles:
    
    - Workflow step execution
    - Error handling and retries
    - Token budgeting and cost tracking
    - Memory management
    - Tool integration
    
    Example:
        >>> engine = WorkflowEngine(openai_api_key="sk-...")
        >>> result = await engine.execute_workflow("document_qa", {"query": "What is AI?"})
        >>> print(result.output)
    """
```

### Error Handling
```python
try:
    result = await execute_workflow(workflow_id, input_data)
except WorkflowNotFoundError as e:
    logger.error(f"Workflow not found: {workflow_id}")
    raise HTTPException(status_code=404, detail=str(e))
except ValidationError as e:
    logger.error(f"Invalid input data: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## 🧪 Testing Guidelines

### Unit Tests
```python
import pytest
from src.core.workflow_engine import WorkflowEngine

@pytest.mark.asyncio
async def test_workflow_execution():
    """Test workflow execution with valid input."""
    engine = WorkflowEngine(openai_api_key="test-key")
    
    result = await engine.execute_workflow(
        workflow_id="test_workflow",
        input_data={"query": "test query"}
    )
    
    assert result.status == "completed"
    assert result.output is not None
    assert result.execution_time_ms > 0
```

### Integration Tests
```python
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_workflow_execution_api():
    """Test workflow execution via API."""
    response = client.post(
        "/api/v1/workflows/execute",
        json={
            "workflow_id": "document_qa",
            "input_data": {"query": "What is AI?"}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
```

### Evaluation Tests
```json
{
  "test_id": "new_test_001",
  "test_type": "workflow",
  "input_data": {
    "query": "What is machine learning?",
    "context": "Machine learning is a subset of artificial intelligence..."
  },
  "expected_output": {
    "answer": "Machine learning is a subset of artificial intelligence...",
    "confidence": 0.9
  },
  "metadata": {
    "workflow_id": "document_qa",
    "category": "knowledge_retrieval"
  }
}
```

## 📝 Commit Message Format

Use conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```
feat(workflow): add conditional step execution
fix(api): resolve memory leak in workflow engine
docs(readme): update installation instructions
test(evaluation): add hallucination detection tests
```

## 🔍 Code Review Process

### What We Look For
- **Functionality**: Does the code work as intended?
- **Testing**: Are there adequate tests?
- **Documentation**: Is the code well-documented?
- **Performance**: Are there any performance implications?
- **Security**: Are there any security concerns?
- **Maintainability**: Is the code easy to understand and maintain?

### Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests are comprehensive and pass
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact is acceptable
- [ ] Security considerations are addressed

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Detailed steps to reproduce
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, dependencies
6. **Logs**: Relevant error messages or logs
7. **Screenshots**: If applicable

## 💡 Feature Requests

When requesting features, please include:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: What alternatives have you considered?
4. **Impact**: How will this affect existing functionality?

## 🏆 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributors page
- Project documentation

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Documentation**: Check existing docs first
- **Code Review**: Ask questions in PR comments

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to the Enterprise GenAI Platform! 🚀
