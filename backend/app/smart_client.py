"""
Smart Query Client - LLM-driven decision making for context-aware, efficient, visualization-first responses
"""

import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import google.generativeai as genai

from .config import settings
from .database import DatabaseManager
from .memory_store import ConversationMemory, get_conversation_memory
from .tools.tool_registry import get_tool_registry

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT - THE BRAIN OF THE SYSTEM
# =============================================================================

SYSTEM_PROMPT = """You are an intelligent data analyst AI that processes natural language queries against a database.

## YOUR CAPABILITIES
1. **Direct SQL Generation** - For simple queries, generate SQL directly
2. **Tool Execution** - For complex analysis, use specialized tools
3. **Visualization Selection** - EVERY response MUST include a visualization
4. **Context Awareness** - Use conversation history to resolve follow-ups

## CONVERSATION MEMORY
{memory_context}

## DATABASE SCHEMA
{schema_context}

## AVAILABLE TOOLS
{tools_context}

## DECISION RULES

### When to use DIRECT SQL (no tools):
- Simple data retrieval: "show me all customers", "list products"
- Basic aggregations: "total sales", "count orders", "average price"
- Simple filters: "sales from last month", "customers in California"
- Follow-up questions that can use previous context

### When to USE TOOLS:
- Anomaly detection: "find unusual patterns", "detect outliers"
- Complex multi-step analysis: "investigate why sales dropped"
- Statistical analysis: "correlation between X and Y"
- Predictive questions: "forecast next month"

### Visualization Selection (MANDATORY for every response):
Based on the DATA TYPE and QUERY INTENT, select ONE:
- **line**: Time series, trends over time, growth patterns
- **bar**: Comparisons, rankings, top/bottom N, category comparisons
- **pie**: Proportions, distributions, market share (use only if ≤8 categories)
- **scatter**: Correlations, relationships between two numeric variables
- **table**: When visualization isn't meaningful (single values, text-heavy data)

## RESPONSE FORMAT
You MUST respond with valid JSON in this exact structure:
```json
{
  "decision": {
    "approach": "direct" | "tools",
    "reasoning": "brief explanation of why this approach",
    "tools_needed": ["tool_name"] or [],
    "uses_memory": true/false
  },
  "sql": "SELECT ... (only if approach is direct, null otherwise)",
  "tool_calls": [
    {"tool": "tool_name", "params": {...}}
  ],
  "visualization": {
    "type": "line" | "bar" | "pie" | "scatter" | "table",
    "x_field": "column_name for x-axis",
    "y_field": "column_name for y-axis", 
    "title": "Chart Title",
    "reasoning": "why this chart type"
  },
  "response_template": "Brief natural language response with {placeholders} for data"
}
```

## EFFICIENCY RULES
1. Prefer DIRECT approach when possible - it's faster
2. Maximum 2 tool calls per query
3. If memory can answer the question, use it
4. Generate efficient SQL with appropriate LIMIT clauses

## IMPORTANT
- ALWAYS include a visualization (even if just "table")
- NEVER explain that you're an AI or apologize
- Be decisive - pick ONE approach
- SQL must be valid PostgreSQL
"""


@dataclass 
class VisualizationConfig:
    chart_type: str
    x_field: str = ""
    y_field: str = ""
    title: str = ""
    reasoning: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "chart_type": self.chart_type,
            "x_field": self.x_field,
            "y_field": self.y_field,
            "title": self.title,
            "reasoning": self.reasoning
        }


@dataclass
class QueryClassification:
    approach: str  # "direct" or "tools"
    reasoning: str
    tools_needed: List[str] = field(default_factory=list)
    uses_memory: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "approach": self.approach,
            "reasoning": self.reasoning,
            "tools_needed": self.tools_needed,
            "uses_memory": self.uses_memory
        }


@dataclass
class SmartQueryResult:
    """Result of a smart query processing"""
    query: str
    sql: Optional[str]
    results: List[Dict[str, Any]]
    visualization: Optional[VisualizationConfig]
    insights: str
    classification: Optional[QueryClassification]
    from_memory: bool
    tools_used: List[str]
    execution_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "sql": self.sql,
            "results": self.results,
            "visualization": self.visualization.to_dict() if self.visualization else None,
            "insights": self.insights,
            "classification": self.classification.to_dict() if self.classification else None,
            "from_memory": self.from_memory,
            "tools_used": self.tools_used,
            "execution_time_ms": self.execution_time_ms
        }


class SmartQueryClient:
    """
    LLM-driven intelligent query client.
    The LLM decides:
    - Whether to use direct SQL or tools
    - What visualization to show
    - How to interpret and respond
    """
    
    def __init__(self, db_manager: DatabaseManager):
        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            top_k=40,
            max_output_tokens=4096,
        )
        
        self.db_manager = db_manager
        self.memory = get_conversation_memory()
        self.tool_registry = get_tool_registry(db_manager)
        self._schema_cache = None
        
        logger.info("🧠 Smart Query Client initialized (LLM-driven)")
    
    async def process_query(self, query: str) -> SmartQueryResult:
        """
        Process query using LLM to make all decisions
        """
        import time
        start_time = time.time()
        
        logger.info(f"🔍 Processing query: '{query}'")
        
        try:
            # Step 1: Get schema (cached)
            schema = await self._get_schema()
            
            # Step 2: Build the system prompt with context
            full_prompt = self._build_full_prompt(query, schema)
            
            # Step 3: Get LLM decision
            decision = await self._get_llm_decision(query, full_prompt)
            
            # Step 4: Execute based on decision
            if decision.get("decision", {}).get("approach") == "tools":
                result = await self._execute_with_tools(query, decision)
            else:
                result = await self._execute_direct(query, decision)
            
            # Step 5: Store in memory
            self._store_in_memory(query, result)
            
            result.execution_time_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ Query processed in {result.execution_time_ms:.0f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Query processing error: {e}")
            return SmartQueryResult(
                query=query,
                sql=None,
                results=[],
                visualization=VisualizationConfig(chart_type="table", title="Error"),
                insights=f"Error processing query: {str(e)}",
                classification=None,
                from_memory=False,
                tools_used=[],
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _get_schema(self) -> Dict:
        """Get database schema (cached)"""
        if self._schema_cache:
            return self._schema_cache
        
        cached = self.memory.get_cached_schema()
        if cached:
            self._schema_cache = cached
            return cached
        
        try:
            result = await self.tool_registry.execute_tool("get_database_schema")
            if result.success:
                self._schema_cache = result.data
                self.memory.cache_schema(result.data)
                return result.data
        except Exception as e:
            logger.warning(f"Schema fetch failed: {e}")
        
        return {}
    
    def _build_full_prompt(self, query: str, schema: Dict) -> str:
        """Build the full system prompt with all context"""
        
        # Memory context
        memory_context = self._format_memory_context()
        
        # Schema context
        schema_context = self._format_schema(schema)
        
        # Tools context
        tools_context = self._format_tools()
        
        # Build prompt
        prompt = SYSTEM_PROMPT.format(
            memory_context=memory_context,
            schema_context=schema_context,
            tools_context=tools_context
        )
        
        return prompt
    
    def _format_memory_context(self) -> str:
        """Format conversation memory for the prompt"""
        if not self.memory.exchanges:
            return "No previous conversation history."
        
        lines = ["Recent conversation history (last 5 exchanges):"]
        for i, exchange in enumerate(self.memory.exchanges[-5:], 1):
            lines.append(f"\n{i}. User: {exchange.user_query}")
            if exchange.sql_generated:
                lines.append(f"   SQL: {exchange.sql_generated[:100]}...")
            if exchange.results_summary:
                lines.append(f"   Results: {exchange.results_summary.get('row_count', 0)} rows")
            if exchange.visualization_type:
                lines.append(f"   Visualization: {exchange.visualization_type}")
            lines.append(f"   Response: {exchange.assistant_response[:100]}...")
        
        return "\n".join(lines)
    
    def _format_schema(self, schema: Dict) -> str:
        """Format schema for the prompt"""
        if not schema or 'tables' not in schema:
            return "Schema not available. Assume common tables: sales, products, customers, markets."
        
        lines = ["Available tables and columns:"]
        for table in schema.get('tables', []):
            name = table.get('name', 'unknown')
            columns = table.get('columns', [])
            col_info = []
            for col in columns[:15]:  # Limit columns
                col_name = col.get('name', '')
                col_type = col.get('type', '')
                col_info.append(f"{col_name}({col_type})")
            lines.append(f"\n• {name}: {', '.join(col_info)}")
        
        return "\n".join(lines)
    
    def _format_tools(self) -> str:
        """Format available tools for the prompt"""
        tool_names = self.tool_registry.list_tools()
        lines = ["Available analysis tools:"]
        
        for name in tool_names:
            tool = self.tool_registry.get_tool(name)
            if tool:
                desc = tool.description[:80] if hasattr(tool, 'description') else "No description"
                lines.append(f"• {name}: {desc}")
        
        return "\n".join(lines)
    
    async def _get_llm_decision(self, query: str, system_prompt: str) -> Dict:
        """Get decision from LLM"""
        
        full_prompt = f"""{system_prompt}

---
USER QUERY: {query}

Respond with ONLY the JSON decision structure. No explanation, just valid JSON."""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                generation_config=self.generation_config
            )
            
            # Parse JSON from response
            response_text = response.text.strip()
            logger.debug(f"Raw LLM response: {response_text[:200]}...")
            
            # Try to extract JSON using multiple methods
            json_str = self._extract_json(response_text)
            
            if json_str:
                decision = json.loads(json_str)
                logger.info(f"📊 LLM Decision: {decision.get('decision', {}).get('approach', 'unknown')}")
                return decision
            else:
                logger.warning("Could not extract JSON from LLM response, using fallback")
                return self._get_fallback_decision(query)
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}, using fallback")
            return self._get_fallback_decision(query)
        except Exception as e:
            logger.error(f"LLM decision error: {e}")
            return self._get_fallback_decision(query)
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text using multiple strategies"""
        import re
        
        text = text.strip()
        
        # Strategy 1: Extract from ```json ... ``` code block
        json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_block_match:
            return json_block_match.group(1).strip()
        
        # Strategy 2: Extract from ``` ... ``` code block
        code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            content = code_block_match.group(1).strip()
            if content.startswith('{'):
                return content
        
        # Strategy 3: Find JSON object directly (starts with { ends with })
        # Look for the outermost { and }
        first_brace = text.find('{')
        if first_brace != -1:
            # Find matching closing brace
            brace_count = 0
            for i, char in enumerate(text[first_brace:], first_brace):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[first_brace:i+1]
                        # Validate it's parseable
                        try:
                            json.loads(json_str)
                            return json_str
                        except:
                            pass
                        break
        
        # Strategy 4: Try the whole text as JSON
        try:
            json.loads(text)
            return text
        except:
            pass
        
        return None
    
    def _get_fallback_decision(self, query: str) -> Dict:
        """Fallback decision when LLM fails - tries to be smart about query type"""
        query_lower = query.lower()
        
        # Determine SQL based on query type
        sql = "SELECT * FROM sales LIMIT 10"  # Default
        viz_type = "table"
        x_field = ""
        y_field = ""
        
        # Schema/database questions
        if any(kw in query_lower for kw in ['schema', 'table', 'database', 'db', 'structure', 'what kind']):
            sql = None  # Will use schema from cache
            viz_type = "table"
        # Count/total questions
        elif any(kw in query_lower for kw in ['count', 'how many', 'total']):
            sql = "SELECT COUNT(*) as total FROM sales"
            viz_type = "table"
        # Sales/revenue questions
        elif any(kw in query_lower for kw in ['sale', 'revenue', 'income']):
            sql = "SELECT DATE_TRUNC('month', sale_date) as month, SUM(revenue) as total_revenue FROM sales GROUP BY month ORDER BY month LIMIT 12"
            viz_type = "line"
            x_field = "month"
            y_field = "total_revenue"
        # Product questions
        elif any(kw in query_lower for kw in ['product', 'item']):
            sql = "SELECT p.product_name, COUNT(*) as sales_count FROM sales s JOIN products p ON s.product_id = p.id GROUP BY p.product_name ORDER BY sales_count DESC LIMIT 10"
            viz_type = "bar"
            x_field = "product_name"
            y_field = "sales_count"
        # Customer questions
        elif any(kw in query_lower for kw in ['customer', 'client', 'user']):
            sql = "SELECT c.customer_name, COUNT(*) as orders FROM sales s JOIN customers c ON s.customer_id = c.id GROUP BY c.customer_name ORDER BY orders DESC LIMIT 10"
            viz_type = "bar"
            x_field = "customer_name"
            y_field = "orders"
        
        return {
            "decision": {
                "approach": "direct",
                "reasoning": "Fallback decision based on query keywords",
                "tools_needed": [],
                "uses_memory": False
            },
            "sql": sql,
            "tool_calls": [],
            "visualization": {
                "type": viz_type,
                "x_field": x_field,
                "y_field": y_field,
                "title": query[:50],
                "reasoning": "Fallback visualization"
            },
            "response_template": "Here are the results for your query."
        }
    
    async def _execute_direct(self, query: str, decision: Dict) -> SmartQueryResult:
        """Execute direct SQL approach"""
        logger.info("⚡ Executing direct SQL approach")
        
        sql = decision.get("sql")
        results = []
        insights = ""
        
        try:
            # Handle schema/database info questions
            query_lower = query.lower()
            if not sql and any(kw in query_lower for kw in ['schema', 'table', 'database', 'db', 'structure', 'what kind']):
                # Return schema information
                schema = await self._get_schema()
                if schema and 'tables' in schema:
                    results = [{"table_name": t.get("name"), "columns": len(t.get("columns", [])), "sample_columns": ", ".join([c.get("name", "") for c in t.get("columns", [])[:5]])} for t in schema.get("tables", [])]
                    insights = f"This is a PostgreSQL database with {len(schema.get('tables', []))} tables: {', '.join([t.get('name', '') for t in schema.get('tables', [])])}. "
                    insights += "The database contains business data including sales, products, customers, and markets information."
                else:
                    insights = "Unable to retrieve database schema information."
            elif sql:
                # Clean SQL
                sql = self._clean_sql(sql)
                results = await self.db_manager.execute_query(sql)
                logger.info(f"📊 Query returned {len(results)} rows")
                
                # Generate insights based on results
                insights = await self._generate_insights(query, results, decision)
            else:
                insights = "No data to display for this query."
            
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            insights = f"Query execution failed: {str(e)}"
        
        # Extract visualization config
        viz_data = decision.get("visualization", {})
        visualization = VisualizationConfig(
            chart_type=viz_data.get("type", "table"),
            x_field=viz_data.get("x_field", ""),
            y_field=viz_data.get("y_field", ""),
            title=viz_data.get("title", query[:50]),
            reasoning=viz_data.get("reasoning", "")
        )
        
        # Extract classification
        dec_data = decision.get("decision", {})
        classification = QueryClassification(
            approach=dec_data.get("approach", "direct"),
            reasoning=dec_data.get("reasoning", ""),
            tools_needed=dec_data.get("tools_needed", []),
            uses_memory=dec_data.get("uses_memory", False)
        )
        
        return SmartQueryResult(
            query=query,
            sql=sql,
            results=results,
            visualization=visualization,
            insights=insights,
            classification=classification,
            from_memory=dec_data.get("uses_memory", False),
            tools_used=[],
            execution_time_ms=0
        )
    
    async def _execute_with_tools(self, query: str, decision: Dict) -> SmartQueryResult:
        """Execute with tools approach"""
        logger.info("🛠️ Executing with tools approach")
        
        tools_used = []
        all_results = []
        tool_insights = []
        sql = decision.get("sql")
        
        try:
            # Execute planned tool calls
            tool_calls = decision.get("tool_calls", [])
            
            for tool_spec in tool_calls[:2]:  # Max 2 tools
                tool_name = tool_spec.get("tool", "")
                tool_params = tool_spec.get("params", {})
                
                if not tool_name:
                    continue
                
                logger.info(f"🔧 Executing tool: {tool_name}")
                
                # Resolve any missing params
                tool_params = await self._resolve_tool_params(tool_name, tool_params, query)
                
                result = await self.tool_registry.execute_tool(tool_name, **tool_params)
                
                if result.success:
                    tools_used.append(tool_name)
                    if result.data:
                        if isinstance(result.data, list):
                            all_results.extend(result.data[:50])
                        elif isinstance(result.data, dict):
                            tool_insights.append(result.data)
                            if 'data' in result.data and isinstance(result.data['data'], list):
                                all_results.extend(result.data['data'][:50])
                else:
                    logger.warning(f"Tool {tool_name} failed: {result.error}")
                
                await asyncio.sleep(0.3)  # Small delay between tools
            
            # If no results from tools, try direct SQL
            if not all_results and sql:
                sql = self._clean_sql(sql)
                all_results = await self.db_manager.execute_query(sql)
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
        
        # Generate insights
        insights = await self._generate_insights(query, all_results, decision, tool_insights)
        
        # Extract visualization config
        viz_data = decision.get("visualization", {})
        visualization = VisualizationConfig(
            chart_type=viz_data.get("type", "table"),
            x_field=viz_data.get("x_field", ""),
            y_field=viz_data.get("y_field", ""),
            title=viz_data.get("title", query[:50]),
            reasoning=viz_data.get("reasoning", "")
        )
        
        # Extract classification
        dec_data = decision.get("decision", {})
        classification = QueryClassification(
            approach=dec_data.get("approach", "tools"),
            reasoning=dec_data.get("reasoning", ""),
            tools_needed=dec_data.get("tools_needed", []),
            uses_memory=dec_data.get("uses_memory", False)
        )
        
        return SmartQueryResult(
            query=query,
            sql=sql,
            results=all_results[:100],
            visualization=visualization,
            insights=insights,
            classification=classification,
            from_memory=False,
            tools_used=tools_used,
            execution_time_ms=0
        )
    
    async def _resolve_tool_params(self, tool_name: str, params: Dict, query: str) -> Dict:
        """Resolve missing parameters for tools"""
        
        # Common defaults based on tool type
        if tool_name == 'detect_revenue_anomalies':
            params.setdefault('table_name', 'sales')
            params.setdefault('revenue_column', 'revenue')
            params.setdefault('threshold_multiplier', 2.0)
            
        elif tool_name == 'detect_time_pattern_anomalies':
            params.setdefault('table_name', 'sales')
            params.setdefault('date_column', 'sale_date')
            params.setdefault('value_column', 'revenue')
            
        elif tool_name == 'get_key_business_metrics':
            pass  # No required params
            
        elif 'chart' in tool_name or 'plot' in tool_name:
            if 'sql_query' not in params:
                # Generate appropriate SQL for the chart
                sql = await self._generate_chart_sql(tool_name, query)
                params['sql_query'] = sql
            params.setdefault('title', query[:50])
            params.setdefault('x_label', 'Category')
            params.setdefault('y_label', 'Value')
        
        return params
    
    async def _generate_chart_sql(self, tool_name: str, query: str) -> str:
        """Generate SQL for chart tools"""
        
        prompt = f"""Generate a simple SQL query for visualization.
Tool: {tool_name}
Query: {query}

Return ONLY PostgreSQL SQL. Default to sales table if unsure.
Example: SELECT product_name, SUM(revenue) as total FROM sales GROUP BY product_name ORDER BY total DESC LIMIT 10
"""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            return self._clean_sql(response.text)
        except:
            return "SELECT product_name, SUM(revenue) as total FROM sales JOIN products ON sales.product_id = products.id GROUP BY product_name ORDER BY total DESC LIMIT 10"
    
    async def _generate_insights(
        self, 
        query: str, 
        results: List[Dict], 
        decision: Dict,
        tool_insights: List[Dict] = None
    ) -> str:
        """Generate natural language insights"""
        
        if not results and not tool_insights:
            return "No data found for your query. Try rephrasing or checking data availability."
        
        # Build context
        context = {
            "query": query,
            "row_count": len(results),
            "columns": list(results[0].keys()) if results else [],
            "sample": results[:3] if results else [],
            "tool_results": tool_insights[:2] if tool_insights else []
        }
        
        template = decision.get("response_template", "")
        
        prompt = f"""Generate concise insights for this data analysis.

Query: {query}
Data Context: {json.dumps(context, default=str)[:1000]}
Response Template Hint: {template}

Provide:
1. Key finding (one clear sentence)
2. Notable patterns (if any)
3. Brief recommendation

Use specific numbers from the data. Keep under 100 words. No preamble."""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Insights error: {e}")
            return f"Found {len(results)} results. Check the visualization for patterns."
    
    def _store_in_memory(self, query: str, result: SmartQueryResult):
        """Store exchange in memory"""
        self.memory.add_exchange(
            user_query=query,
            assistant_response=result.insights,
            sql_generated=result.sql,
            results_summary={
                "row_count": len(result.results),
                "columns": list(result.results[0].keys()) if result.results else []
            },
            visualization_type=result.visualization.chart_type if result.visualization else None,
            tools_used=result.tools_used
        )
    
    def _clean_sql(self, sql: str) -> str:
        """Clean SQL string"""
        if not sql:
            return ""
        sql = sql.strip()
        if sql.startswith('```sql'):
            sql = sql[6:]
        if sql.startswith('```'):
            sql = sql[3:]
        if sql.endswith('```'):
            sql = sql[:-3]
        return sql.strip()
    
    def get_memory_state(self) -> Dict[str, Any]:
        """Get current memory state"""
        return self.memory.get_memory_state()
    
    def clear_memory(self) -> None:
        """Clear conversation memory"""
        self.memory.clear()
        self._schema_cache = None


# Global instance
_smart_client: Optional[SmartQueryClient] = None


def get_smart_client(db_manager: DatabaseManager) -> SmartQueryClient:
    """Get or create the global smart client instance"""
    global _smart_client
    if _smart_client is None:
        _smart_client = SmartQueryClient(db_manager)
    return _smart_client
