import time
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import QueryRequest, QueryResponse, SQLResponse, ErrorResponse, SchemaInput
from .gemini_client import GeminiClient
from .database import DatabaseManager


app = FastAPI(
    title="NL2SQL API with Gemini",
    description="Natural Language to SQL Query System using Google Gemini 2.5 Pro",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
gemini_client = GeminiClient()
db_manager = DatabaseManager()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "NL2SQL API with Gemini is running", 
        "version": "1.0.0",
        "model": "Gemini 2.5 Pro"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    
    # Test database connection
    db_status = "connected" if await db_manager.test_connection() else "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "database": db_status,
            "gemini": "configured" if settings.gemini_api_key else "not_configured"
        }
    }


@app.post("/generate-sql", response_model=SQLResponse)
async def generate_sql(request: QueryRequest):
    """Generate SQL from natural language query"""
    
    try:
        # Validate inputs
        if not request.schema_text.strip():
            raise HTTPException(status_code=400, detail="Schema is required")
        
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Generate SQL using Gemini
        sql_response = await gemini_client.nl_to_sql(
            user_query=request.query,
            schema=request.schema_text
        )
        
        if not sql_response.sql.strip():
            raise HTTPException(status_code=500, detail="Failed to generate SQL")
        
        return sql_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQL generation failed: {str(e)}"
        )


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """Generate SQL and execute it against the database"""
    
    start_time = time.time()
    
    try:
        # Validate inputs
        if not request.schema_text.strip():
            raise HTTPException(status_code=400, detail="Schema is required")
        
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Generate SQL using Gemini
        sql_response = await gemini_client.nl_to_sql(
            user_query=request.query,
            schema=request.schema_text
        )
        
        if not sql_response.sql.strip():
            raise HTTPException(status_code=500, detail="Failed to generate SQL")
        
        # Execute SQL query
        try:
            results = await db_manager.execute_query(sql_response.sql)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"SQL execution failed: {str(e)}"
            )
        
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000
        
        return QueryResponse(
            sql=sql_response.sql,
            explanation=sql_response.explanation,
            results=results,
            row_count=len(results),
            execution_time_ms=execution_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@app.post("/validate-schema")
async def validate_schema(schema_input: SchemaInput):
    """Validate user-provided schema format"""
    
    try:
        schema_text = schema_input.schema_text.strip()
        
        if not schema_text:
            raise HTTPException(status_code=400, detail="Schema text is required")
        
        # Basic validation - check if it looks like a schema
        schema_lower = schema_text.lower()
        
        # Should contain table-like structures
        has_table_keywords = any(keyword in schema_lower for keyword in [
            'table', 'create', 'column', 'field', 'primary key', 'foreign key'
        ])
        
        if not has_table_keywords:
            return {
                "valid": False,
                "message": "Schema should contain table definitions with columns and relationships"
            }
        
        return {
            "valid": True,
            "message": "Schema format appears valid",
            "tables_detected": schema_lower.count('table'),
            "length": len(schema_text)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Schema validation failed: {str(e)}"
        )


@app.post("/test-sql")
async def test_sql_execution(sql_query: Dict[str, str]):
    """Test SQL execution without generating from NL"""
    
    try:
        sql = sql_query.get("sql", "").strip()
        
        if not sql:
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        # Execute SQL query
        start_time = time.time()
        results = await db_manager.execute_query(sql)
        execution_time_ms = (time.time() - start_time) * 1000
        
        return {
            "sql": sql,
            "results": results,
            "row_count": len(results),
            "execution_time_ms": execution_time_ms
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"SQL execution failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )