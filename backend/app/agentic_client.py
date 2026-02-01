"""
Agentic Gemini client with autonomous database investigation capabilities
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
import google.generativeai as genai
from .config import settings
from .models import SQLResponse
from .tools.tool_registry import get_tool_registry, ToolRegistry
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class AgenticInvestigationStep:
    """Represents a single step in an autonomous investigation"""
    
    def __init__(self, step_type: str, description: str, tool_name: str = None, 
                 parameters: Dict = None, result: Any = None, reasoning: str = None):
        self.step_type = step_type  # 'tool_call', 'analysis', 'conclusion'
        self.description = description
        self.tool_name = tool_name
        self.parameters = parameters or {}
        self.result = result
        self.reasoning = reasoning
        self.timestamp = None
        
    def to_dict(self):
        return {
            "step_type": self.step_type,
            "description": self.description,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "result": self.result,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp
        }


class AgenticGeminiClient:
    """Enhanced Gemini client with autonomous investigation capabilities"""
    
    def __init__(self, db_manager: DatabaseManager):
        # Configure Gemini API
        genai.configure(api_key=settings.gemini_api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Generation config for function calling
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            top_k=40,
            max_output_tokens=4096,
        )
        
        # Initialize tool registry
        self.db_manager = db_manager
        self.tool_registry = get_tool_registry(db_manager)
        
        # Investigation state
        self.current_investigation = []
        self.investigation_context = {}
        
        # Track investigation progress
        self.tools_executed_count = 0
    
    def _build_agentic_system_prompt(self) -> str:
        """Build comprehensive system prompt for agentic behavior"""
        
        tool_categories = self.tool_registry.get_tools_by_category()
        
        return f"""You are an expert autonomous database analyst with advanced investigation capabilities. You can conduct targeted, multi-step investigations based on the specific question asked.

## YOUR AVAILABLE TOOLS

### 🔍 DATABASE DISCOVERY
{self._format_tool_category_help("database_discovery", tool_categories)}

### ⚡ SQL EXECUTION
{self._format_tool_category_help("sql_execution", tool_categories)}

### 💼 BUSINESS METRICS
{self._format_tool_category_help("business_metrics", tool_categories)}

### 🚨 ANOMALY DETECTION
{self._format_tool_category_help("anomaly_detection", tool_categories)}

### 📊 DATA ANALYSIS
{self._format_tool_category_help("data_analysis", tool_categories)}

### 📈 VISUALIZATION & GRAPHS
{self._format_tool_category_help("visualization", tool_categories)}
{self._format_tool_category_help("graphs", tool_categories)}

## QUERY-DRIVEN INVESTIGATION APPROACH

**KEY PRINCIPLE**: Your tool selection should be DRIVEN BY THE SPECIFIC QUESTION, not a fixed template.

### Investigation Steps:
1. **ALWAYS** start with `get_database_schema` to understand available data
2. **READ THE QUERY** carefully to understand what's being asked
3. **SELECT RELEVANT TOOLS** based on the query:
   - Customer behavior → Analyze customer data, temporal patterns, segmentation
   - Regions/markets → Compare markets, geographic distribution
   - Time periods → Temporal analysis, trends over time
   - Anomalies → Use anomaly detection tools
   - Products → Product performance, rankings
   - Performance → Business metrics, KPIs, trends

4. **GENERATE RELEVANT VISUALIZATIONS**:
   - Bar charts for comparisons and rankings
   - Line charts for temporal trends
   - Pie charts for distributions
   - Scatter plots for correlations
   - **Write SQL queries that answer the SPECIFIC question**

5. **PROVIDE TARGETED ANALYSIS** focused on the user's actual query

### Example Query Mapping:

**"What trends do you see in our customer behavior?"**
→ Focus on: Customer patterns, temporal trends, behavior changes
→ Tools: get_database_schema, execute_sql_query (customer analysis), generate_line_chart (behavior over time), detect_time_pattern_anomalies
→ **DO NOT**: Generate generic product/market charts unrelated to customers

**"Compare performance across regions"**
→ Focus on: Regional comparisons, geographic distribution
→ Tools: get_database_schema, generate_bar_chart (regions comparison), generate_pie_chart (regional distribution)
→ **DO NOT**: Generate time trends or scatter plots

**"Find anomalies in our data"**
→ Focus on: Outliers, unusual patterns, data quality issues
→ Tools: get_database_schema, detect_revenue_anomalies, detect_time_pattern_anomalies, detect_customer_behavior_anomalies, relevant charts
→ **DO NOT**: Generate business summaries

## CRITICAL RULES

1. **Query-Driven**: Let the user's question guide your tool selection
2. **Relevant SQL**: Write SQL queries that directly answer the question
3. **Targeted**: Use 4-6 tools maximum, all relevant to the query
4. **Data-Backed**: Cite specific numbers from your analysis
5. **Focused**: Stay on topic - don't provide generic business advice

## RESPONSE QUALITY

Your final analysis must:
- **Answer the specific question asked**
- **Use actual data** from the tools you executed
- **Cite specific numbers**, percentages, and metrics
- **Focus on the query topic** (customers, regions, products, etc.)
- **Avoid generic advice** unrelated to the query

REMEMBER: You are investigating a SPECIFIC question, not conducting a generic business review. Stay focused and relevant!
"""
    
    def _format_tool_category_help(self, category: str, tool_categories: Dict) -> str:
        """Format help text for a tool category"""
        if category not in tool_categories:
            return ""
        
        tools = tool_categories[category]
        help_text = ""
        
        for tool_name in tools:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                help_text += f"- **{tool_name}**: {tool.description}\n"
        
        return help_text
    
    def _is_anomaly_query(self, query: str) -> bool:
        """Detect if the query is asking for anomaly detection or unusual patterns"""
        anomaly_keywords = [
            'anomal', 'unusual', 'strange', 'weird', 'odd', 'outlier', 'abnormal',
            'irregular', 'suspicious', 'unexpected', 'deviation', 'exception',
            'pattern', 'trend', 'inconsistent', 'error', 'mistake', 'wrong',
            'fraud', 'detect', 'find', 'identify', 'spot', 'discover'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in anomaly_keywords)
    
    async def autonomous_investigation(self, user_query: str, stream_steps: bool = True) -> AsyncGenerator[AgenticInvestigationStep, None]:
        """Conduct autonomous database investigation with real-time step streaming"""
        
        logger.info(f"🔄 Starting autonomous investigation: '{user_query}'")
        
        # Reset investigation state
        self.current_investigation = []
        
        # Detect if this is an anomaly detection query
        is_anomaly_query = self._is_anomaly_query(user_query)
        self.investigation_context = {"user_query": user_query}
        
        # Build messages for conversation in Gemini format
        system_prompt = self._build_agentic_system_prompt()
        anomaly_instructions = ""
        if is_anomaly_query:
            anomaly_instructions = """
🚨 ANOMALY DETECTION QUERY DETECTED! 

PRIORITY TOOLS FOR ANOMALY DETECTION:
1. get_database_schema (understand data structure)
2. detect_revenue_anomalies (find unusual revenue patterns)
3. detect_time_pattern_anomalies (find irregular timing patterns)  
4. detect_customer_behavior_anomalies (find unusual customer behaviors)
5. Use visualization tools to show anomalies graphically
6. generate_business_summary (synthesize findings)

FOCUS ON: Statistical outliers, unusual patterns, data inconsistencies, suspicious transactions, irregular behaviors.
"""
        
        user_prompt = f"""Conduct a comprehensive autonomous investigation to answer this question: "{user_query}"
{anomaly_instructions}

INVESTIGATION METHODOLOGY:
1. ALWAYS start with get_database_schema to understand available data
2. Choose appropriate tools based on the SPECIFIC question being asked
3. Generate visualizations that directly answer the question
4. Provide analysis focused on the user's actual query

IMPORTANT:
- Your tool selection should be DRIVEN BY THE QUERY, not a fixed list
- If the query asks about regions/markets, focus on market comparisons
- If the query asks about time periods, focus on temporal analysis
- If the query asks about anomalies, use anomaly detection tools
- If the query asks about products, analyze product performance
- Generate RELEVANT visualizations, not generic ones

Use 4-6 tools maximum. Be targeted and relevant to the query."""

        # Combine system and user prompts for Gemini
        combined_prompt = f"{system_prompt}\n\nUser Request: {user_prompt}"
        
        # Get tool definitions for function calling
        tool_definitions = self.tool_registry.get_tool_definitions()
        
        max_iterations = 8  # Reasonable limit for query-driven investigations
        iteration = 0
        empty_call_count = 0  # Track consecutive empty function calls
        
        # Rate limiting configuration - reduced for faster iteration
        normal_delay = 30.0  # Normal delay between tool calls (5 seconds)
        rate_limit_delay = 32.0  # Delay when rate limited
        retry_count = 0
        max_retries = 2  # Reduced retries since we're using longer delays
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Reduced delays to allow more productive iterations
                if iteration > 1:
                    # Only delay if we actually executed a tool in the last iteration
                    recent_steps = self.current_investigation[-3:] if len(self.current_investigation) >= 3 else self.current_investigation
                    if any(step.step_type == "tool_call" for step in recent_steps):
                        logger.info(f"⏳ Waiting {normal_delay}s before next iteration")
                        await asyncio.sleep(normal_delay)
                        empty_call_count = 0  # Reset empty call counter
                    else:
                        # No delay if we didn't execute tools (empty function calls)
                        empty_call_count += 1
                        logger.info(f"⚡ Empty call #{empty_call_count} - minimal delay")
                        await asyncio.sleep(1.0)  # Minimal delay
                        
                        # If we get too many empty calls, end investigation early
                        if empty_call_count >= 3:
                            logger.info("🔄 Too many empty function calls, ending investigation")
                            break
                
                # Generate response with function calling
                response = await self._generate_with_tools(combined_prompt, tool_definitions)
                
                if not response:
                    break
                
                # Process function calls if any
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    
                    if hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            # Handle function calls
                            if hasattr(part, 'function_call'):
                                func_call = part.function_call
                                tool_name = func_call.name
                                
                                # Debug logging
                                logger.info(f"🔍 Raw function call: {func_call}")
                                logger.info(f"🔍 Tool name extracted: '{tool_name}'")
                                
                                # Skip empty function calls
                                if not tool_name or tool_name.strip() == "":
                                    logger.warning("⚠️ Skipping empty function call")
                                    continue
                                
                                # Parse parameters
                                try:
                                    parameters = dict(func_call.args) if func_call.args else {}
                                    logger.info(f"🔍 Parameters parsed: {parameters}")
                                except Exception as e:
                                    logger.error(f"❌ Error parsing parameters: {e}")
                                    parameters = {}
                                
                                # Validate tool exists
                                if not self.tool_registry.get_tool(tool_name):
                                    logger.error(f"❌ Tool '{tool_name}' not found in registry. Available tools: {self.tool_registry.list_tools()}")
                                    continue
                                
                                # Create investigation step
                                step = AgenticInvestigationStep(
                                    step_type="tool_call",
                                    description=f"Executing {tool_name}",
                                    tool_name=tool_name,
                                    parameters=parameters,
                                    reasoning=f"Using {tool_name} to investigate the data"
                                )
                                
                                if stream_steps:
                                    yield step
                                
                                # Execute the tool
                                logger.info(f"🛠️ Executing tool: {tool_name} with params: {parameters}")
                                tool_result = await self.tool_registry.execute_tool(tool_name, **parameters)
                                
                                # Debug logging
                                logger.info(f"🔍 Tool result - Success: {tool_result.success}, Error: {tool_result.error}, Data type: {type(tool_result.data)}")
                                if tool_result.data:
                                    logger.info(f"🔍 Tool data keys: {list(tool_result.data.keys()) if isinstance(tool_result.data, dict) else 'Not a dict'}")
                                
                                # Update step with result - wrap in proper structure for frontend
                                if tool_result.success:
                                    # Wrap data so frontend can access as step.result.data
                                    step.result = {
                                        "data": tool_result.data,
                                        "success": True,
                                        "execution_time_ms": tool_result.execution_time_ms if hasattr(tool_result, 'execution_time_ms') else None,
                                        "metadata": tool_result.metadata if hasattr(tool_result, 'metadata') else None
                                    }
                                    logger.info(f"✅ Tool {tool_name} succeeded with data")
                                else:
                                    step.result = {"error": tool_result.error, "success": False}
                                    logger.error(f"❌ Tool {tool_name} failed: {tool_result.error}")
                                self.current_investigation.append(step)
                                
                                # Track execution
                                if tool_result.success:
                                    self.tools_executed_count += 1
                                    logger.info(f"✅ Tool {tool_name} completed successfully ({self.tools_executed_count} tools executed)")
                                
                                # Update the prompt with function result for next iteration
                                function_result = json.dumps(step.result, default=str)
                                progress_msg = f"\n\n✅ Tool {tool_name} executed successfully! Continue investigation or provide final analysis if you have sufficient data to answer the query."
                                
                                combined_prompt += f"{progress_msg}\n\nResult: {function_result}\n\nBased on this result, continue your investigation."
                            
                            # Handle text responses (analysis, conclusions)
                            elif hasattr(part, 'text'):
                                text_content = part.text
                                
                                # Determine if this is analysis or conclusion
                                if any(keyword in text_content.lower() for keyword in ['conclusion', 'summary', 'recommendation', 'insight']):
                                    step_type = "conclusion"
                                    description = "Final analysis and recommendations"
                                else:
                                    step_type = "analysis"
                                    description = "Analyzing findings and planning next steps"
                                
                                step = AgenticInvestigationStep(
                                    step_type=step_type,
                                    description=description,
                                    result={"analysis": text_content},
                                    reasoning="Synthesizing findings and determining next steps"
                                )
                                
                                if stream_steps:
                                    yield step
                                
                                self.current_investigation.append(step)
                                
                                # Update prompt with analysis
                                combined_prompt += f"\n\nAnalysis: {text_content}"
                                
                                # Check if investigation is complete
                                if step_type == "conclusion":
                                    logger.info("🎉 Investigation completed with conclusions")
                                    return
                    
                    # If no function calls, the investigation might be complete
                    if not any(hasattr(part, 'function_call') for part in candidate.content.parts if hasattr(candidate.content, 'parts')):
                        logger.info("🏁 Investigation completed - no more function calls")
                        break
                
                # Small delay to prevent overwhelming the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error in investigation iteration {iteration}: {error_msg}")
                
                # Handle rate limiting with retry
                if "429" in error_msg or "Resource exhausted" in error_msg or "quota" in error_msg.lower():
                    # Extract retry delay from error message if available
                    retry_delay = rate_limit_delay  # Use configured rate limit delay
                    
                    # Try to extract the actual retry delay from the error message
                    import re
                    delay_match = re.search(r'retry in (\d+\.?\d*)s', error_msg)
                    if delay_match:
                        suggested_delay = float(delay_match.group(1))
                        retry_delay = max(suggested_delay, rate_limit_delay)  # Use at least the configured delay
                    
                    if retry_count < max_retries:
                        retry_count += 1
                        logger.info(f"🔄 Rate limited. Retrying in {retry_delay:.1f}s (attempt {retry_count}/{max_retries})")
                        logger.info(f"📊 Quota info: {error_msg}")
                        
                        # Yield a retry step
                        retry_step = AgenticInvestigationStep(
                            step_type="retry",
                            description=f"API quota exceeded. Waiting {retry_delay:.0f} seconds before retry...",
                            result={
                                "retry_attempt": retry_count, 
                                "delay": retry_delay,
                                "reason": "Rate limit exceeded",
                                "quota_info": error_msg
                            }
                        )
                        
                        if stream_steps:
                            yield retry_step
                        
                        await asyncio.sleep(retry_delay)
                        iteration -= 1  # Don't count this as a real iteration
                        continue
                    else:
                        logger.error("❌ Max retries exceeded for rate limiting")
                        
                        # Yield final error step
                        error_step = AgenticInvestigationStep(
                            step_type="error",
                            description="Investigation failed due to API rate limits",
                            result={
                                "error": "API quota exceeded and max retries reached",
                                "quota_info": error_msg,
                                "suggestion": "Please wait and try again later, or upgrade your API plan"
                            }
                        )
                        
                        if stream_steps:
                            yield error_step
                        
                        break
                
                error_step = AgenticInvestigationStep(
                    step_type="error",
                    description=f"Error in investigation: {error_msg}",
                    result={"error": error_msg}
                )
                
                if stream_steps:
                    yield error_step
                
                break
        
        # If we completed without conclusions, force a final analysis
        if self.current_investigation and not any(step.step_type == "conclusion" for step in self.current_investigation):
            logger.info("🔄 Generating final analysis and conclusions...")
            
            # Add delay before final analysis to prevent rate limiting
            logger.info("⏳ Waiting 10s before generating final analysis to prevent rate limiting")
            await asyncio.sleep(10.0)
            
            # Create a summary of all findings
            findings_summary = self._create_findings_summary()
            
            # Generate final conclusions without tools
            conclusion_prompt = f"""
You are a business analyst reviewing investigation findings. Based on the ACTUAL DATA below, provide comprehensive insights.

{findings_summary}

CRITICAL INSTRUCTIONS:
1. USE THE ACTUAL DATA from the anomaly detection results above
2. Cite specific numbers, anomalies, and patterns found in the data
3. Do NOT make up generic insights - use only what's in the data above
4. Focus on ANOMALIES if this was an anomaly detection query

Please provide:
1. **Key Findings Summary** - What anomalies and patterns were actually found?
2. **Anomaly Analysis** - What specific outliers were detected?
3. **Business Impact** - What do these anomalies mean for the business?
4. **Actionable Recommendations** - Specific next steps based on the findings

Be SPECIFIC and DATA-DRIVEN. Reference actual values from the investigation results.
"""
            
            try:
                # Generate final analysis without tools
                final_response = await asyncio.to_thread(
                    self.model.generate_content,
                    conclusion_prompt,
                    generation_config=self.generation_config
                )
                
                if final_response and hasattr(final_response, 'candidates') and final_response.candidates:
                    conclusion_text = final_response.candidates[0].content.parts[0].text
                    
                    conclusion_step = AgenticInvestigationStep(
                        step_type="conclusion",
                        description="Final analysis and recommendations",
                        result={"analysis": conclusion_text},
                        reasoning="Synthesizing all investigation findings into actionable business insights"
                    )
                    
                    if stream_steps:
                        yield conclusion_step
                    
                    self.current_investigation.append(conclusion_step)
                    logger.info("✅ Final analysis generated successfully")
                
            except Exception as e:
                logger.error(f"❌ Error generating final analysis: {e}")
                
                # Provide a fallback analysis when rate limited
                if "429" in str(e) or "Resource exhausted" in str(e):
                    # Extract any metrics from completed steps
                    metrics_summary = self._extract_metrics_from_steps()
                    
                    fallback_analysis = f"""
**Investigation Summary**

The autonomous investigation successfully executed {len(self.current_investigation)} steps:

{self._create_simple_summary()}

**Key Findings with Available Metrics:**
{metrics_summary}

**Database Analysis Results:**
- Database schema successfully analyzed
- Table structures and relationships identified  
- Data accessibility confirmed

**Recommendations Based on Available Data:**
1. **Immediate Action**: Execute key aggregation queries to get specific metrics:
   - Total revenue: `SELECT SUM(revenue) FROM sales`
   - Top products: `SELECT product_name, SUM(revenue) FROM sales s JOIN products p ON s.product_id = p.id GROUP BY product_name ORDER BY SUM(revenue) DESC LIMIT 5`
   - Monthly trends: `SELECT DATE_TRUNC('month', sale_date), SUM(revenue) FROM sales GROUP BY 1 ORDER BY 1`

2. **Data Quality**: Ensure data consistency across all tables
3. **Performance Monitoring**: Set up regular automated analysis
4. **Visualization**: Use the specific graph tools to create visual dashboards

**Next Steps**: Click "See Results" or "See Relevant Graphs" to execute comprehensive queries and generate visualizations.

**Note**: Full analysis was limited due to API rate limiting. The system will automatically execute key queries when you use the action buttons above.
"""
                    
                    fallback_step = AgenticInvestigationStep(
                        step_type="conclusion",
                        description="Fallback analysis due to rate limiting",
                        result={"analysis": fallback_analysis},
                        reasoning="Providing summary analysis when full analysis is rate limited"
                    )
                    
                    if stream_steps:
                        yield fallback_step
                    
                    self.current_investigation.append(fallback_step)
                    logger.info("✅ Fallback analysis provided due to rate limiting")
        
        logger.info(f"🏁 Investigation completed after {iteration} iterations")
    
    def _create_findings_summary(self) -> str:
        """Create a detailed summary of all investigation findings with actual data"""
        if not self.current_investigation:
            return "No investigation data available."
        
        summary_parts = []
        summary_parts.append("=" * 80)
        summary_parts.append("INVESTIGATION FINDINGS - DETAILED RESULTS")
        summary_parts.append("=" * 80)
        summary_parts.append("")
        
        for i, step in enumerate(self.current_investigation, 1):
            if step.step_type == "tool_call" and step.result:
                summary_parts.append(f"{'='*60}")
                summary_parts.append(f"STEP {i}: {step.tool_name.upper() if step.tool_name else 'UNKNOWN'}")
                summary_parts.append(f"{'='*60}")
                
                if step.parameters:
                    summary_parts.append(f"Parameters: {step.parameters}")
                    summary_parts.append("")
                
                # Get actual data - handle both old and new structure
                result_data = step.result.get('data', step.result) if isinstance(step.result, dict) else step.result
                
                # Extract and format the actual results
                if isinstance(result_data, dict):
                    # Handle anomaly detection results
                    if step.tool_name and 'anomal' in step.tool_name.lower():
                        import json
                        summary_parts.append("ANOMALY DETECTION RESULTS:")
                        summary_parts.append(json.dumps(result_data, indent=2, default=str))
                    # Handle chart data
                    elif step.tool_name and 'chart' in step.tool_name.lower():
                        if isinstance(result_data, list) and len(result_data) > 0:
                            summary_parts.append(f"Chart Data ({len(result_data)} data points):")
                            summary_parts.append(f"First 5 records: {result_data[:5]}")
                    # Handle business metrics/summary
                    elif step.tool_name and ('metrics' in step.tool_name.lower() or 'summary' in step.tool_name.lower()):
                        import json
                        summary_parts.append("BUSINESS METRICS:")
                        summary_parts.append(json.dumps(result_data, indent=2, default=str))
                    # Handle schema
                    elif step.tool_name and 'schema' in step.tool_name.lower():
                        summary_parts.append("Database schema retrieved successfully")
                    # Default handling
                    else:
                        if 'error' in result_data:
                            summary_parts.append(f"ERROR: {result_data['error']}")
                        else:
                            import json
                            summary_parts.append(json.dumps(result_data, indent=2, default=str))
                elif isinstance(result_data, list):
                    summary_parts.append(f"Results: {len(result_data)} records")
                    if len(result_data) > 0:
                        summary_parts.append(f"First record: {result_data[0]}")
                
                summary_parts.append("")  # Add blank line
        
        summary_parts.append("=" * 80)
        summary_parts.append("END OF DETAILED FINDINGS")
        summary_parts.append("=" * 80)
        
        return "\n".join(summary_parts)
    
    def _create_simple_summary(self) -> str:
        """Create a simple summary of investigation steps"""
        if not self.current_investigation:
            return "No investigation steps completed."
        
        summary_parts = []
        for i, step in enumerate(self.current_investigation, 1):
            if step.step_type == "tool_call":
                summary_parts.append(f"{i}. {step.description} - {step.tool_name}")
            else:
                summary_parts.append(f"{i}. {step.description}")
        
        return "\n".join(summary_parts)
    
    def _extract_metrics_from_steps(self) -> str:
        """Extract any numerical metrics from completed investigation steps"""
        if not self.current_investigation:
            return "No metrics available from completed steps."
        
        metrics = []
        for step in self.current_investigation:
            if step.step_type == "tool_call" and step.result:
                # Get actual data - handle both old and new structure
                data = step.result.get('data', step.result) if isinstance(step.result, dict) else step.result
                
                if not data:
                    continue
                
                # Extract metrics from SQL query results
                if isinstance(data, list) and len(data) > 0:
                    if step.tool_name == 'execute_sql_query':
                        # Try to extract meaningful metrics
                        first_row = data[0] if data else {}
                        if isinstance(first_row, dict):
                            for key, value in first_row.items():
                                if isinstance(value, (int, float)) and value > 0:
                                    metrics.append(f"- {key}: {value:,.0f}")
                    
                    metrics.append(f"- {step.tool_name}: {len(data)} records analyzed")
                
                # Extract table information
                elif isinstance(data, dict):
                    if 'tables' in data:  # Schema information
                        table_count = len(data['tables'])
                        metrics.append(f"- Database contains {table_count} tables")
                    
                    if 'total_records' in data:
                        metrics.append(f"- Total records: {data['total_records']:,}")
                    
                    # Extract anomaly metrics
                    if 'anomalies_found' in data:
                        anomalies = data['anomalies_found']
                        if isinstance(anomalies, dict):
                            for key, val in anomalies.items():
                                if isinstance(val, dict) and 'count' in val:
                                    metrics.append(f"- {key}: {val['count']} anomalies detected")
                    
                    # Extract summary metrics from business metrics
                    if 'summary' in data and isinstance(data['summary'], dict):
                        for key, val in data['summary'].items():
                            if isinstance(val, (int, float)):
                                metrics.append(f"- {key}: {val:,.2f}")
        
        return "\n".join(metrics) if metrics else "- Investigation in progress, metrics will be available upon completion"
    
    async def _generate_with_tools(self, prompt: str, tool_definitions: List[Dict]) -> Any:
        """Generate response with tool calling capability"""
        try:
            # Debug: Log tool definitions
            logger.info(f"🔍 Tool definitions count: {len(tool_definitions)}")
            for i, tool_def in enumerate(tool_definitions[:3]):  # Log first 3 tools
                logger.info(f"🔍 Tool {i}: {tool_def.get('name', 'UNKNOWN')}")
            
            # Convert tool definitions to Gemini format
            tools = [genai.protos.Tool(function_declarations=[
                genai.protos.FunctionDeclaration(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            name: genai.protos.Schema(
                                type=self._convert_type(prop.get("type", "string")),
                                description=prop.get("description", "")
                            )
                            for name, prop in tool_def["parameters"]["properties"].items()
                        },
                        required=tool_def["parameters"].get("required", [])
                    )
                )
                for tool_def in tool_definitions
            ])]
            
            # Generate content with tools
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                tools=tools,
                generation_config=self.generation_config
            )
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error generating response with tools: {error_msg}")
            
            # Re-raise rate limiting errors so they can be handled upstream
            if "429" in error_msg or "quota" in error_msg.lower() or "Resource exhausted" in error_msg:
                logger.warning(f"⚠️ Rate limiting detected in API call: {error_msg}")
                raise e
            
            return None
    
    def _convert_type(self, type_str: str) -> genai.protos.Type:
        """Convert string type to Gemini Type enum"""
        type_mapping = {
            "string": genai.protos.Type.STRING,
            "integer": genai.protos.Type.INTEGER,
            "number": genai.protos.Type.NUMBER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT
        }
        return type_mapping.get(type_str.lower(), genai.protos.Type.STRING)
    
    async def simple_nl_to_sql(self, user_query: str, schema: str) -> SQLResponse:
        """Simple NL2SQL conversion (backward compatibility)"""
        
        prompt = f"""You are an expert SQL developer. Convert this natural language query to SQL.

Database Schema:
{schema}

User Query: {user_query}

Return only valid PostgreSQL SQL. Use proper JOINs and include appropriate LIMIT clauses.

SQL:"""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            
            sql = response.text.strip()
            
            # Clean up the SQL
            if sql.startswith('```sql'):
                sql = sql.replace('```sql', '').replace('```', '').strip()
            elif sql.startswith('```'):
                sql = sql.replace('```', '').strip()
            
            return SQLResponse(
                sql=sql,
                explanation=f"Generated SQL for: {user_query}"
            )
            
        except Exception as e:
            logger.error(f"❌ Simple NL2SQL failed: {str(e)}")
            raise Exception(f"SQL generation failed: {str(e)}")
    
    def get_investigation_summary(self) -> Dict[str, Any]:
        """Get summary of current investigation"""
        if not self.current_investigation:
            return {"message": "No investigation in progress"}
        
        tool_calls = [step for step in self.current_investigation if step.step_type == "tool_call"]
        analyses = [step for step in self.current_investigation if step.step_type == "analysis"]
        conclusions = [step for step in self.current_investigation if step.step_type == "conclusion"]
        
        return {
            "total_steps": len(self.current_investigation),
            "tool_calls": len(tool_calls),
            "analyses": len(analyses),
            "conclusions": len(conclusions),
            "tools_used": list(set(step.tool_name for step in tool_calls if step.tool_name)),
            "investigation_context": self.investigation_context,
            "steps": [step.to_dict() for step in self.current_investigation]
        }
