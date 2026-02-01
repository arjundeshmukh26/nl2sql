import time
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import QueryRequest, QueryResponse, SQLResponse, ErrorResponse, SchemaInput, AgenticQueryRequest
from .gemini_client import GeminiClient
from .agentic_client import AgenticGeminiClient, AgenticInvestigationStep
from .database import DatabaseManager
from .tools.tool_registry import initialize_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

# Initialize agentic system
tool_registry = initialize_tools(db_manager)
agentic_client = AgenticGeminiClient(db_manager)


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
            logger.info(f"🔄 Executing SQL query...")
            results = await db_manager.execute_query(sql_response.sql)
            logger.info(f"✅ Query executed successfully, returned {len(results)} rows")
        except Exception as e:
            error_msg = f"SQL execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"🔍 Failed SQL: {sql_response.sql}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            sql=sql_response.sql,
            explanation=sql_response.explanation,
            results=results,
            row_count=len(results),
            execution_time_ms=execution_time_ms,
            suggested_chart_type="table"  # Default - actual chart type decided by LLM in visualization endpoint
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific API quota errors
        if "429" in error_msg and "quota" in error_msg.lower():
            logger.warning(f"⚠️ API quota exceeded: {error_msg}")
            raise HTTPException(
                status_code=429,
                detail="API quota exceeded. Please wait before making more requests or upgrade your API plan."
            )
        elif "rate limit" in error_msg.lower():
            logger.warning(f"⚠️ Rate limit hit: {error_msg}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait a moment before trying again."
            )
        else:
            logger.error(f"❌ Query processing failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Query processing failed: {error_msg}"
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


@app.post("/generate-insights")
async def generate_insights(request: Dict[str, Any]):
    """Generate insights based on user query and results"""
    
    try:
        user_query = request.get("user_query", "")
        results = request.get("results", [])
        sql = request.get("sql", "")
        
        if not user_query or not results:
            raise HTTPException(status_code=400, detail="User query and results are required")
        
        # Generate insights using Gemini
        insights_prompt = f"""
You are a data analyst. Analyze the following query results and provide actionable business insights.

Original User Query: "{user_query}"
SQL Query: {sql}

Results Summary:
- Total rows: {len(results)}
- Sample data: {results[:5] if results else []}

Provide 3-5 key insights in bullet points focusing on:
1. Key findings and patterns
2. Business implications
3. Actionable recommendations
4. Notable trends or anomalies

Format as clear, concise bullet points.
"""
        
        logger.info(f"🧠 Generating insights for query: '{user_query}'")
        response = gemini_client.model.generate_content(
            insights_prompt,
            generation_config=gemini_client.generation_config
        )
        
        insights = response.text.strip()
        logger.info(f"💡 Generated insights: {insights[:200]}..." if len(insights) > 200 else f"💡 Generated insights: {insights}")
        
        return {
            "insights": insights,
            "data_summary": {
                "total_rows": len(results),
                "columns": list(results[0].keys()) if results else [],
                "sample_data": results[:3] if results else []
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific API quota errors
        if "429" in error_msg and "quota" in error_msg.lower():
            logger.warning(f"⚠️ API quota exceeded: {error_msg}")
            raise HTTPException(
                status_code=429,
                detail="API quota exceeded. Please wait before making more requests or upgrade your API plan."
            )
        elif "rate limit" in error_msg.lower():
            logger.warning(f"⚠️ Rate limit hit: {error_msg}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait a moment before trying again."
            )
        else:
            logger.error(f"❌ Insights generation failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Insights generation failed: {error_msg}"
            )


@app.post("/generate-visualization")
async def generate_visualization(request: Dict[str, Any]):
    """Generate visualization configuration based on results"""
    
    try:
        user_query = request.get("user_query", "")
        results = request.get("results", [])
        sql = request.get("sql", "")
        
        if not user_query or not results:
            raise HTTPException(status_code=400, detail="User query and results are required")
        
        # Analyze data structure for visualization
        columns = list(results[0].keys()) if results else []
        sample_data = results[:10] if results else []
        
        # Generate aggregation query if needed for better visualization
        aggregation_prompt = f"""
Based on this data and user query, generate a SQL aggregation query that would be better for visualization.

Original Query: "{user_query}"
Original SQL: {sql}
Columns: {columns}
Sample Data: {sample_data[:3]}
Total Rows: {len(results)}

IMPORTANT: The original query returned {len(results)} rows. 
If this is 0 or very few rows, DO NOT create a more complex aggregation - just use the original SQL with an appropriate chart type.

Chart Type Guidelines:
- BAR: Categories vs values, comparisons, rankings
- LINE: Time series, trends over time (non-cumulative)
- PIE: Parts of a whole, percentages, simple distributions (max 8 slices)
- DOUGHNUT: Parts of a whole grouped by higher-level category (e.g., by region)
- SCATTER: Correlation between two continuous variables
- AREA: Cumulative or progressive totals over time (e.g., revenue growth)
- RADAR: Multi-dimensional metrics comparison (e.g., avg revenue, avg quantity, avg price per category)

Rules:
1. If original query has 0 rows, return the original SQL unchanged
2. If original query has < 15 rows, ALWAYS keep the original SQL - it's already perfect for visualization
3. If the data already has aggregated columns (like totals, percentages, counts), use original SQL
4. Only create aggregation if original has > 20 rows AND needs grouping/summarization
5. Choose the most appropriate chart type based on data characteristics:
   - Use DOUGHNUT if grouping by region or other high-level categories
   - Use RADAR if multiple numeric metrics per category are present
   - Use AREA if cumulative or running totals are implied
6. Return JSON format: {{
    "sql": "original_sql_here",
    "chart_type": "bar|line|pie|scatter|area|doughnut|radar",
    "explanation": "why this chart type - mention using original data"
}}

IMPORTANT:
- For queries with < 15 rows that already contain aggregated data, ALWAYS use the original SQL unchanged.
- Encourage using different chart types based on semantics rather than defaulting to bar or line.
"""

        
        logger.info(f"📊 Generating visualization for query: '{user_query}'")
        response = gemini_client.model.generate_content(
            aggregation_prompt,
            generation_config=gemini_client.generation_config
        )
        
        # Parse response
        viz_config = response.text.strip()
        logger.info(f"🎨 Raw visualization response: {viz_config}")
        
        # Try to parse as JSON
        try:
            if viz_config.startswith('```json'):
                viz_config = viz_config.replace('```json', '').replace('```', '').strip()
            elif viz_config.startswith('```'):
                viz_config = viz_config.replace('```', '').strip()
            
            import json
            viz_data = json.loads(viz_config)
            logger.info(f"📈 Parsed visualization config: {viz_data}")
            
            # For small datasets (<=15 rows), always use original data
            if len(results) <= 15:
                logger.info(f"📊 Small dataset ({len(results)} rows) - using original data for visualization")
                viz_data["aggregated_data"] = results
                viz_data["sql"] = sql  # Force use of original SQL
                viz_data["explanation"] = f"Using original data ({len(results)} rows) - perfect size for visualization"
                
                # Detailed logging of the data being sent
                logger.info(f"🔍 Original results structure: {type(results)}")
                logger.info(f"🔍 Original results length: {len(results)}")
                if results:
                    logger.info(f"🔍 First row keys: {list(results[0].keys())}")
                    logger.info(f"🔍 First row values: {list(results[0].values())}")
                    logger.info(f"🔍 Sample data: {results[:2]}")
                
                logger.info(f"🔍 viz_data keys: {list(viz_data.keys())}")
                logger.info(f"🔍 aggregated_data type: {type(viz_data['aggregated_data'])}")
                logger.info(f"🔍 aggregated_data length: {len(viz_data['aggregated_data'])}")
                if viz_data['aggregated_data']:
                    logger.info(f"🔍 aggregated_data sample: {viz_data['aggregated_data'][:2]}")
            # Execute the aggregation query if different from original and dataset is large
            elif viz_data.get("sql") and viz_data["sql"] != sql:
                logger.info(f"🔄 Large dataset - executing aggregation query: {viz_data['sql']}")
                agg_results = await db_manager.execute_query(viz_data["sql"])
                viz_data["aggregated_data"] = agg_results
                logger.info(f"📊 Aggregation results: {len(agg_results)} rows")
                
                # If aggregation returns no data, fall back to original results
                if len(agg_results) == 0:
                    logger.warning(f"⚠️ Aggregation query returned no data, using original results")
                    viz_data["aggregated_data"] = results
                    viz_data["sql"] = sql  # Use original SQL
                    viz_data["explanation"] = "Using original data - aggregation returned no results"
            else:
                logger.info("📊 Using original data for visualization")
                viz_data["aggregated_data"] = results
                
        except json.JSONDecodeError:
            # Fallback to original data
            viz_data = {
                "sql": sql,
                "chart_type": "bar",
                "explanation": "Using original data",
                "aggregated_data": results
            }
        
        # Final data preparation for frontend
        final_data = viz_data.get("aggregated_data", [])
        final_chart_type = viz_data.get("chart_type", "bar")
        final_explanation = viz_data.get("explanation", "")
        
        logger.info(f"🎯 Final response preparation:")
        logger.info(f"🎯 Chart type: {final_chart_type}")
        logger.info(f"🎯 Data type: {type(final_data)}")
        logger.info(f"🎯 Data length: {len(final_data) if final_data else 0}")
        logger.info(f"🎯 Explanation: {final_explanation}")
        
        if final_data:
            logger.info(f"🎯 Final data sample: {final_data[:2]}")
            logger.info(f"🎯 First row structure: {final_data[0] if final_data else 'No data'}")
        else:
            logger.error(f"❌ CRITICAL: No data in final response!")
        
        response_data = {
            "chart_type": final_chart_type,
            "data": final_data,
            "explanation": final_explanation
        }
        
        logger.info(f"🚀 Sending response to frontend: {response_data}")
        
        return response_data
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific API quota errors
        if "429" in error_msg and "quota" in error_msg.lower():
            logger.warning(f"⚠️ API quota exceeded: {error_msg}")
            raise HTTPException(
                status_code=429,
                detail="API quota exceeded. Please wait before making more requests or upgrade your API plan."
            )
        elif "rate limit" in error_msg.lower():
            logger.warning(f"⚠️ Rate limit hit: {error_msg}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait a moment before trying again."
            )
        else:
            logger.error(f"❌ Visualization generation failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Visualization generation failed: {error_msg}"
            )


@app.post("/agentic-investigation")
async def start_agentic_investigation(request: AgenticQueryRequest):
    """Start an autonomous database investigation"""
    
    start_time = time.time()
    
    try:
        # Validate inputs
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query is required")
        
        logger.info(f"🚀 Starting agentic investigation: '{request.query}'")
        
        # Collect all investigation steps
        investigation_steps = []
        
        async for step in agentic_client.autonomous_investigation(request.query, stream_steps=True):
            investigation_steps.append(step.to_dict())
        
        # Get investigation summary
        summary = agentic_client.get_investigation_summary()
        
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000
        
        return {
            "query": request.query,
            "investigation_steps": investigation_steps,
            "summary": summary,
            "execution_time_ms": execution_time_ms,
            "total_steps": len(investigation_steps),
            "tools_used": summary.get("tools_used", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Agentic investigation failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {error_msg}"
        )


@app.get("/tools")
async def list_available_tools():
    """Get list of all available tools and their capabilities"""
    
    try:
        tool_help = tool_registry.get_tool_help()
        tool_stats = tool_registry.get_tool_usage_stats()
        
        return {
            "available_tools": tool_help,
            "usage_statistics": tool_stats,
            "total_tools": len(tool_registry.list_tools()),
            "tool_categories": tool_registry.get_tools_by_category()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting tools info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tools information: {str(e)}"
        )


@app.post("/execute-tool")
async def execute_single_tool(tool_request: dict):
    """Execute a single tool for testing purposes"""
    
    try:
        tool_name = tool_request.get("tool_name")
        parameters = tool_request.get("parameters", {})
        
        if not tool_name:
            raise HTTPException(status_code=400, detail="tool_name is required")
        
        logger.info(f"🛠️ Executing tool: {tool_name} with params: {parameters}")
        
        result = await tool_registry.execute_tool(tool_name, **parameters)
        
        return {
            "tool_name": tool_name,
            "parameters": parameters,
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
            "metadata": result.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Tool execution failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed: {error_msg}"
        )


@app.get("/test-schema")
async def test_database_schema():
    """Test database schema retrieval directly"""
    try:
        logger.info("🧪 Testing database schema retrieval")
        
        # Execute the schema tool directly
        result = await tool_registry.execute_tool("get_database_schema")
        
        return {
            "success": result.success,
            "data": result.data if result.success else None,
            "error": result.error if not result.success else None,
            "execution_time_ms": result.execution_time_ms,
            "metadata": result.metadata
        }
        
    except Exception as e:
        logger.error(f"❌ Schema test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Schema test failed: {str(e)}"
        )


@app.get("/list-models")
async def list_gemini_models():
    """List available Gemini models"""
    try:
        import google.generativeai as genai
        
        logger.info("🔍 Listing available Gemini models")
        
        # Configure API using existing settings
        genai.configure(api_key=settings.gemini_api_key)
        
        # Get all available models
        models = list(genai.list_models())
        
        model_info = []
        generation_models = []
        
        for model in models:
            info = {
                "name": model.name,
                "display_name": model.display_name,
                "supported_methods": list(model.supported_generation_methods) if hasattr(model, 'supported_generation_methods') else []
            }
            
            if hasattr(model, 'description'):
                info["description"] = model.description
            
            model_info.append(info)
            
            # Check if it supports generateContent
            if 'generateContent' in info["supported_methods"]:
                generation_models.append(model.name)
        
        logger.info(f"✅ Found {len(models)} total models, {len(generation_models)} support generateContent")
        
        return {
            "success": True,
            "total_models": len(models),
            "all_models": model_info,
            "generation_models": generation_models,
            "recommended": generation_models[0] if generation_models else None
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )