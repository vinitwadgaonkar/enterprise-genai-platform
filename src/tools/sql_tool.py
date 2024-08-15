"""
SQL execution tool with safety checks and result formatting.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Union
import asyncpg
import pandas as pd
from .base import BaseTool, ToolResult
import structlog

logger = structlog.get_logger(__name__)


class SQLTool(BaseTool):
    """Tool for executing SQL queries with safety checks."""
    
    def __init__(
        self, 
        connection_string: str,
        max_rows: int = 100,
        timeout_seconds: int = 30,
        **kwargs
    ):
        super().__init__(
            name="sql_tool",
            description="Execute SQL queries with safety checks and result formatting",
            **kwargs
        )
        self.connection_string = connection_string
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.pool = None
        
        # Dangerous SQL patterns
        self.dangerous_patterns = [
            r'\bDROP\b',
            r'\bDELETE\b',
            r'\bTRUNCATE\b',
            r'\bALTER\b',
            r'\bCREATE\b',
            r'\bINSERT\b',
            r'\bUPDATE\b',
            r'\bGRANT\b',
            r'\bREVOKE\b',
            r'\bEXEC\b',
            r'\bEXECUTE\b',
            r'\bCALL\b'
        ]
    
    async def initialize(self):
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=self.timeout_seconds
            )
            logger.info("Initialized SQL tool connection pool")
        except Exception as e:
            logger.error(f"Failed to initialize SQL tool: {e}")
            raise
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Closed SQL tool connection pool")
    
    def _validate_query(self, query: str) -> tuple[bool, str]:
        """Validate SQL query for safety."""
        query_upper = query.upper().strip()
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, query_upper):
                return False, f"Query contains potentially dangerous operation: {pattern}"
        
        # Check for SELECT-only queries
        if not query_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        # Check for subqueries with dangerous operations
        if re.search(r'\([^)]*(?:DROP|DELETE|INSERT|UPDATE)', query_upper):
            return False, "Query contains dangerous operations in subqueries"
        
        return True, "Query is safe"
    
    def _format_results(self, rows: List[tuple], columns: List[str]) -> Dict[str, Any]:
        """Format query results for display."""
        if not rows:
            return {
                "data": [],
                "columns": columns,
                "row_count": 0,
                "message": "No results found"
            }
        
        # Convert to list of dictionaries
        data = []
        for row in rows:
            row_dict = {}
            for i, value in enumerate(row):
                column_name = columns[i] if i < len(columns) else f"column_{i}"
                # Convert non-serializable types
                if isinstance(value, (bytes, memoryview)):
                    row_dict[column_name] = str(value)
                elif hasattr(value, 'isoformat'):  # datetime objects
                    row_dict[column_name] = value.isoformat()
                else:
                    row_dict[column_name] = value
            data.append(row_dict)
        
        return {
            "data": data,
            "columns": columns,
            "row_count": len(data),
            "message": f"Retrieved {len(data)} rows"
        }
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute a SQL query."""
        if not self.pool:
            await self.initialize()
        
        try:
            # Validate query
            is_safe, message = self._validate_query(query)
            if not is_safe:
                return ToolResult(
                    success=False,
                    data=None,
                    error=message
                )
            
            # Execute query with timeout
            async with self.pool.acquire() as conn:
                # Set statement timeout
                await conn.execute(f"SET statement_timeout = {self.timeout_seconds * 1000}")
                
                # Execute query
                rows = await conn.fetch(query)
                
                # Limit results
                if len(rows) > self.max_rows:
                    rows = rows[:self.max_rows]
                    truncated = True
                else:
                    truncated = False
                
                # Get column names
                columns = list(rows[0].keys()) if rows else []
                
                # Format results
                formatted_data = self._format_results([tuple(row) for row in rows], columns)
                
                # Add truncation info
                if truncated:
                    formatted_data["message"] += f" (truncated to {self.max_rows} rows)"
                    formatted_data["truncated"] = True
                else:
                    formatted_data["truncated"] = False
                
                return ToolResult(
                    success=True,
                    data=formatted_data,
                    metadata={
                        "query": query,
                        "execution_time_ms": 0,  # Could be measured
                        "row_count": len(rows),
                        "truncated": truncated
                    }
                )
        
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                data=None,
                error=f"Query timed out after {self.timeout_seconds} seconds"
            )
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"SQL execution failed: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for SQL tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL SELECT query to execute"
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    
    async def get_table_schema(self, table_name: str) -> ToolResult:
        """Get schema information for a table."""
        if not self.pool:
            await self.initialize()
        
        try:
            query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = $1
            ORDER BY ordinal_position
            """
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, table_name)
                
                schema_data = {
                    "table_name": table_name,
                    "columns": [
                        {
                            "name": row["column_name"],
                            "type": row["data_type"],
                            "nullable": row["is_nullable"] == "YES",
                            "default": row["column_default"]
                        }
                        for row in rows
                    ]
                }
                
                return ToolResult(
                    success=True,
                    data=schema_data,
                    metadata={"table_name": table_name}
                )
        
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to get table schema: {str(e)}"
            )
    
    async def list_tables(self) -> ToolResult:
        """List all tables in the database."""
        if not self.pool:
            await self.initialize()
        
        try:
            query = """
            SELECT table_name, table_type
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                
                tables = [
                    {
                        "name": row["table_name"],
                        "type": row["table_type"]
                    }
                    for row in rows
                ]
                
                return ToolResult(
                    success=True,
                    data={"tables": tables},
                    metadata={"count": len(tables)}
                )
        
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to list tables: {str(e)}"
            )
