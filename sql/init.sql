-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL,
    chunk_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-large dimension
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create index for document_id lookups
CREATE INDEX IF NOT EXISTS embeddings_document_id_idx ON embeddings (document_id);

-- Create index for metadata queries
CREATE INDEX IF NOT EXISTS embeddings_metadata_idx ON embeddings USING GIN (metadata);

-- Create workflow executions table
CREATE TABLE IF NOT EXISTS workflow_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    token_usage JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create index for workflow executions
CREATE INDEX IF NOT EXISTS workflow_executions_workflow_id_idx ON workflow_executions (workflow_id);
CREATE INDEX IF NOT EXISTS workflow_executions_status_idx ON workflow_executions (status);
CREATE INDEX IF NOT EXISTS workflow_executions_created_at_idx ON workflow_executions (created_at);

-- Create conversation memory table
CREATE TABLE IF NOT EXISTS conversation_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_type VARCHAR(50) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for conversation memory
CREATE INDEX IF NOT EXISTS conversation_memory_session_id_idx ON conversation_memory (session_id);
CREATE INDEX IF NOT EXISTS conversation_memory_created_at_idx ON conversation_memory (created_at);

-- Create evaluation results table
CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL,
    test_type VARCHAR(100) NOT NULL,  -- 'golden_answer', 'hallucination', 'cost'
    input_data JSONB,
    expected_output JSONB,
    actual_output JSONB,
    score DECIMAL(5,4),
    metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for evaluation results
CREATE INDEX IF NOT EXISTS evaluation_results_test_name_idx ON evaluation_results (test_name);
CREATE INDEX IF NOT EXISTS evaluation_results_test_type_idx ON evaluation_results (test_type);
CREATE INDEX IF NOT EXISTS evaluation_results_created_at_idx ON evaluation_results (created_at);
