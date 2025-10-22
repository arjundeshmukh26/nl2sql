from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class SchemaInput(BaseModel):
    """User-provided database schema in data model format"""
    schema_text: str
    description: Optional[str] = None


class QueryRequest(BaseModel):
    """Request model for natural language query"""
    schema_text: str  # User-provided schema
    query: str   # Natural language query
    

class SQLResponse(BaseModel):
    """Response model for generated SQL"""
    sql: str
    explanation: Optional[str] = None


class QueryResponse(BaseModel):
    """Complete response with SQL and results"""
    sql: str
    explanation: Optional[str] = None
    results: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    details: Optional[str] = None