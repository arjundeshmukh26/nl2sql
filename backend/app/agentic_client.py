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
from .memory_store import get_conversation_memory, ConversationMemory

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
        
        # Initialize the model (using lite version for higher rate limits)
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
        
        # Initialize conversation memory
        self.memory = get_conversation_memory()
        
        # Investigation state
        self.current_investigation = []
        self.investigation_context = {}
        
        # Track investigation progress
        self.tools_executed_count = 0
        
        # Track executed tool calls to prevent duplicates
        self.executed_tool_signatures = set()
    
    def _build_agentic_system_prompt(self) -> str:
        """Build comprehensive system prompt for agentic behavior with memory awareness"""
        
        tool_categories = self.tool_registry.get_tools_by_category()
        
        # Get memory context
        memory_context = self._get_memory_context_for_prompt()
        
        return f"""You are an expert autonomous database analyst with advanced investigation capabilities and CONVERSATION MEMORY. You can conduct targeted investigations while being smart about when to use tools vs. when to answer from existing context.

## 🧠 CONVERSATION MEMORY & CONTEXT

{memory_context}

## ⚡ QUERY COMPLEXITY ASSESSMENT (CRITICAL - READ FIRST!)

Before making ANY tool calls, you MUST assess the query complexity:

### SIMPLE QUERIES (Answer WITHOUT or with MINIMAL tool calls):
- **Follow-up questions** about previous results ("what about...", "more details on...", "show me that again")
- **Clarifications** of previous responses ("explain that", "what did you mean by...")
- **References to recent data** ("the same data but...", "that query", "those results")
- **General knowledge questions** about the data you've already seen
- **Simple aggregations** you can calculate from memory context
- **General Questions** about the database and its data etc or other such question that does not require tool calls.
For simple queries:
1. If it is straightforward question that can be answered from memory, answer directly without calling any tools.
2. First call `get_conversation_context` to check what's in memory
3. If the answer exists in context, respond directly WITHOUT additional database queries
4. Only generate a visualization if one wasn't already provided for similar data

### MODERATE QUERIES (Use 2-4 tools):
- Questions needing ONE new piece of data combined with existing context
- Slight variations on previous queries ("same analysis but for different region")
- Basic comparisons that need fresh data

### COMPLEX QUERIES (Full investigation - 4-6 tools):
- Brand new topics not discussed before
- Multi-faceted analysis requests
- Deep-dive investigations
- Anomaly detection requests
- Comprehensive business analysis

## 🎯 DECISION FLOW

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│ Is this a follow-up or reference    │
│ to previous conversation?           │
└─────────────────────────────────────┘
    │YES                    │NO
    ▼                       ▼
┌─────────────────┐   ┌─────────────────┐
│ get_conversation│   │ Is this a       │
│ _context FIRST  │   │ simple factual  │
└─────────────────┘   │ question?       │
    │                 └─────────────────┘
    ▼                       │YES    │NO
┌─────────────────┐         ▼       ▼
│ Can answer from │   ┌─────────┐ ┌─────────┐
│ memory alone?   │   │Minimal  │ │Full     │
└─────────────────┘   │tools    │ │invest-  │
   │YES    │NO        │(1-2)    │ │igation  │
   ▼       ▼          └─────────┘ └─────────┘
┌──────┐ ┌──────┐
│Answer│ │Fetch │
│direct│ │delta │
│ly    │ │only  │
└──────┘ └──────┘
```

## 📊 MANDATORY VISUALIZATION RULE

**EVERY response MUST include AT LEAST ONE visualization/graph**, regardless of query complexity:

1. **Even for simple queries**: Generate at least one appropriate chart
2. **Chart selection guide**:
   - Comparisons/Rankings → `generate_bar_chart`
   - Trends over time → `generate_line_chart`  
   - Distributions/Proportions → `generate_pie_chart`
   - Correlations/Relationships → `generate_scatter_plot`
3. **If data exists in memory**: You can reuse/reference previous visualizations OR generate a new one with slightly different parameters
4. **Minimum requirement**: At least ONE graph tool call per response

## 🧰 YOUR AVAILABLE TOOLS

### 🧠 MEMORY & CONTEXT (USE FIRST FOR FOLLOW-UPS!)
{self._format_tool_category_help("memory_context", tool_categories)}

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

### 📈 VISUALIZATION & GRAPHS (MANDATORY - At least ONE per response!)
{self._format_tool_category_help("visualization", tool_categories)}
{self._format_tool_category_help("graphs", tool_categories)}

## SMART INVESTIGATION APPROACH

### For Follow-up Queries:
1. Call `get_conversation_context` FIRST
2. Check if answer exists in memory
3. If yes → Answer directly + generate one relevant visualization
4. If no → Fetch only the NEW data needed + visualization

### For New Queries:
1. Start with `get_database_schema` (unless recently cached)
2. Execute targeted SQL/analysis if required
3. **ALWAYS** generate at least one visualization if it is possible and makes sense for that query.
4. Provide data-backed insights

### Example Smart Responses:

**User: "What were the top products again?"**
→ Complexity: SIMPLE (follow-up)
→ Action: `get_conversation_context` → Check if answered before → Answer from memory + `generate_bar_chart`

**User: "Show me sales by region"**  
→ Complexity: MODERATE (new but simple)
→ Action: `get_database_schema` (if needed) → `generate_bar_chart` with region SQL → Answer

**User: "Do a deep analysis of customer behavior anomalies"**
→ Complexity: COMPLEX (deep investigation)
→ Action: Full investigation with 5-6 tools including multiple visualizations

## CRITICAL RULES

1. **General Questions** about the database and its data etc or other such question that does not require tool calls.
2. **Memory First**: Always check conversation context for follow-ups
3. **Smart Tool Use**: Don't repeat expensive queries if data is in memory
4. **Mandatory Graphs**: EVERY response needs at least ONE visualization
5. **Efficient**: Use minimum tools needed to answer the query
6. **Data-Backed**: Always cite specific numbers from your analysis
7. **Context-Aware**: Build on previous conversations, don't start fresh every time
8. **NO DUPLICATE TOOL CALLS**: NEVER call the same tool with the same parameters twice! Once a tool has returned data, use that data - do NOT call it again. If you've already generated a bar chart for "revenue by region", do NOT generate another one. Move on to different analysis or provide your final conclusion.

## RESPONSE FORMAT

For EVERY response, ensure:
✅ At least one visualization/graph
✅ Specific data points and numbers  
✅ Direct answer to the user's question
✅ Efficient tool usage based on query complexity
✅ The response is strictly relevant to the original query. 
"""
    
    def _get_memory_context_for_prompt(self) -> str:
        """Get formatted memory context to include in system prompt"""
        if not self.memory.exchanges:
            return """**No previous conversation context available.**
This is a fresh conversation - you should conduct a full investigation for the user's query."""
        
        context_parts = [f"**You have memory of the last {len(self.memory.exchanges)} conversation(s).**"]
        context_parts.append("\n### Recent Conversation Summary:")
        
        for i, exchange in enumerate(list(self.memory.exchanges)[-3:], 1):
            context_parts.append(f"\n**Exchange {i}:**")
            context_parts.append(f"- User asked: \"{exchange.user_query[:100]}{'...' if len(exchange.user_query) > 100 else ''}\"")
            if exchange.sql_generated:
                context_parts.append(f"- SQL used: `{exchange.sql_generated[:80]}...`")
            if exchange.visualization_type:
                context_parts.append(f"- Visualization: {exchange.visualization_type}")
            if exchange.tools_used:
                context_parts.append(f"- Tools used: {', '.join(exchange.tools_used[:5])}")
        
        tables = self.memory.get_mentioned_tables()
        if tables:
            context_parts.append(f"\n**Tables discussed:** {', '.join(tables)}")
        
        context_parts.append("\n\n**Use `get_conversation_context` tool to retrieve full details when needed for follow-up queries.**")
        
        return "\n".join(context_parts)
    
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
        self.executed_tool_signatures = set()  # Reset duplicate tracking
        
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
        duplicate_call_count = 0  # Track consecutive duplicate tool calls
        
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
                
                # Check if too many duplicate calls - force termination
                if duplicate_call_count >= 3:
                    logger.info("🔄 Too many duplicate tool calls detected, forcing termination")
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
                                
                                # Create a signature for this tool call to detect duplicates
                                # Sort parameters for consistent hashing
                                param_str = json.dumps(parameters, sort_keys=True, default=str)
                                tool_signature = f"{tool_name}:{param_str}"
                                
                                # Check for duplicate tool calls
                                if tool_signature in self.executed_tool_signatures:
                                    duplicate_call_count += 1
                                    logger.warning(f"⚠️ Skipping duplicate tool call: {tool_name} (duplicate #{duplicate_call_count})")
                                    # Add instruction to prompt to not repeat this tool
                                    combined_prompt += f"\n\n⚠️ DUPLICATE DETECTED: You already called {tool_name} with the same parameters. DO NOT call it again. Either use different parameters, call a different tool, or provide your final analysis."
                                    
                                    # If too many duplicates, terminate investigation
                                    if duplicate_call_count >= 2:
                                        logger.info("🔄 Too many duplicate tool calls, forcing conclusion")
                                        combined_prompt += "\n\n🛑 STOP: You have been repeating the same tool calls. Please provide your FINAL ANALYSIS now based on all the data collected so far. Do NOT call any more tools."
                                    continue
                                
                                # Add to executed signatures and reset duplicate counter on successful new call
                                self.executed_tool_signatures.add(tool_signature)
                                duplicate_call_count = 0  # Reset on successful unique tool call
                                
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
            # Determine the query type to customize the analysis
            original_query = self.current_investigation[0].description if self.current_investigation else "unknown query"
            
            conclusion_prompt = f"""
You are a senior business analyst reviewing database investigation findings. Your task is to provide comprehensive, data-driven insights.

ORIGINAL USER QUERY: {original_query}

{findings_summary}

CRITICAL INSTRUCTIONS:
1. USE ONLY THE ACTUAL DATA shown above - cite specific numbers, values, and statistics
2. Reference the exact figures from the investigation (e.g., "$13,970.00 for North region")
3. Do NOT make up generic insights - every claim must be backed by data above
4. Compare and contrast values where relevant (e.g., "North is 43% higher than South")
5. Identify the highest, lowest, trends, and outliers in the data

Please provide a comprehensive analysis with these sections:

## 1. Key Findings Summary
- What are the main insights from the data?
- What patterns or trends are visible?
- Cite specific numbers from each visualization/query result

## 2. Data Analysis
- Compare the different data points (highest vs lowest, etc.)
- Calculate percentages and differences where relevant
- Identify any anomalies or outliers in the data

## 3. Business Impact
- What do these numbers mean for the business?
- What opportunities or risks does the data reveal?
- Which areas need attention based on the metrics?

## 4. Actionable Recommendations
- Specific, prioritized next steps based on the findings
- What further analysis would be valuable?
- Quick wins vs long-term improvements

FORMAT: Use markdown with headers, bullet points, and bold for key numbers.
TONE: Professional but accessible, like presenting to executives.
LENGTH: Comprehensive but concise - every sentence should add value.
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
                    # Extract actual data from completed steps
                    metrics_summary = self._extract_metrics_from_steps()
                    steps_summary = self._create_simple_summary()
                    
                    # Count successful tool calls
                    successful_tools = [s for s in self.current_investigation if s.step_type == "tool_call" and s.result]
                    viz_count = len([s for s in successful_tools if s.tool_name and 'chart' in s.tool_name.lower()])
                    
                    fallback_analysis = f"""
## Investigation Summary

The autonomous investigation successfully executed **{len(self.current_investigation)} steps** with **{len(successful_tools)} successful tool calls** and generated **{viz_count} visualizations**.

### Steps Completed:
{steps_summary}

---

## Key Findings from Collected Data

{metrics_summary}

---

## Analysis & Insights

Based on the data collected during this investigation:

1. **Data Coverage**: The investigation successfully queried the database and retrieved relevant metrics.

2. **Visualization Status**: {viz_count} chart(s) were generated to visualize the data. Scroll up to view them in the investigation steps.

3. **Data Quality**: The queries executed successfully, indicating good data integrity.

---

## Recommendations

1. **Review Visualizations**: Check the generated charts above for visual insights into the data patterns.

2. **Deep Dive Analysis**: For more detailed analysis, consider:
   - Breaking down metrics by different time periods
   - Comparing performance across regions/categories
   - Identifying top/bottom performers

3. **Next Steps**: Use the investigation steps above to understand the data flow and results.

---

*Note: Detailed LLM analysis was limited due to API rate constraints. The data shown above is extracted directly from the completed investigation steps.*
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
        import json
        
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
                summary_parts.append(f"Description: {step.description}")
                summary_parts.append(f"{'='*60}")
                
                if step.parameters:
                    summary_parts.append(f"Parameters: {json.dumps(step.parameters, default=str)}")
                    summary_parts.append("")
                
                result = step.result
                
                # Handle visualization tool results (bar chart, line chart, pie chart, scatter plot)
                if step.tool_name and any(chart in step.tool_name.lower() for chart in ['chart', 'plot', 'graph']):
                    summary_parts.append(f"VISUALIZATION: {result.get('title', 'Chart')}")
                    summary_parts.append(f"Chart Type: {result.get('chart_type', 'unknown')}")
                    
                    chart_data = result.get('chart_data', {})
                    if chart_data:
                        # Extract labels and values for bar/pie charts
                        if 'labels' in chart_data and 'values' in chart_data:
                            labels = chart_data['labels']
                            values = chart_data['values']
                            summary_parts.append(f"\nDATA ({len(labels)} items):")
                            for label, value in zip(labels, values):
                                if isinstance(value, (int, float)):
                                    summary_parts.append(f"  • {label}: {value:,.2f}")
                                else:
                                    summary_parts.append(f"  • {label}: {value}")
                            
                            # Calculate totals and stats
                            if all(isinstance(v, (int, float)) for v in values):
                                total = sum(values)
                                avg = total / len(values) if values else 0
                                max_val = max(values) if values else 0
                                min_val = min(values) if values else 0
                                max_label = labels[values.index(max_val)] if values else "N/A"
                                min_label = labels[values.index(min_val)] if values else "N/A"
                                summary_parts.append(f"\nSTATISTICS:")
                                summary_parts.append(f"  • Total: {total:,.2f}")
                                summary_parts.append(f"  • Average: {avg:,.2f}")
                                summary_parts.append(f"  • Highest: {max_label} ({max_val:,.2f})")
                                summary_parts.append(f"  • Lowest: {min_label} ({min_val:,.2f})")
                        
                        # Extract datasets for line charts
                        if 'datasets' in chart_data:
                            labels = chart_data.get('labels', [])
                            summary_parts.append(f"\nTIME SERIES DATA (periods: {len(labels)}):")
                            if labels:
                                summary_parts.append(f"  Period range: {labels[0]} to {labels[-1]}")
                            
                            for ds in chart_data['datasets']:
                                ds_name = ds.get('label', 'Series')
                                ds_values = ds.get('data', [])
                                if ds_values and all(isinstance(v, (int, float)) for v in ds_values if v is not None):
                                    valid_values = [v for v in ds_values if v is not None]
                                    total = sum(valid_values)
                                    avg = total / len(valid_values) if valid_values else 0
                                    summary_parts.append(f"  • {ds_name}: Total={total:,.2f}, Avg={avg:,.2f}")
                
                # Handle anomaly detection results
                elif step.tool_name and 'anomal' in step.tool_name.lower():
                    summary_parts.append("ANOMALY DETECTION RESULTS:")
                    summary_parts.append(json.dumps(result, indent=2, default=str))
                
                # Handle SQL query results
                elif step.tool_name == 'execute_sql_query':
                    data = result.get('data', result) if isinstance(result, dict) else result
                    if isinstance(data, list):
                        summary_parts.append(f"SQL QUERY RESULTS ({len(data)} rows):")
                        for row in data[:10]:  # Show first 10 rows
                            if isinstance(row, dict):
                                row_parts = []
                                for k, v in row.items():
                                    if isinstance(v, (int, float)):
                                        row_parts.append(f"{k}={v:,.2f}")
                                    else:
                                        row_parts.append(f"{k}={v}")
                                summary_parts.append(f"  • {', '.join(row_parts)}")
                
                # Handle comparison results
                elif step.tool_name and 'compare' in step.tool_name.lower():
                    summary_parts.append("TIME PERIOD COMPARISON RESULTS:")
                    if 'error' in result:
                        summary_parts.append(f"  ERROR: {result['error']}")
                    else:
                        summary_parts.append(json.dumps(result, indent=2, default=str))
                
                # Handle business metrics
                elif step.tool_name and ('metrics' in step.tool_name.lower() or 'summary' in step.tool_name.lower()):
                    summary_parts.append("BUSINESS METRICS:")
                    summary_parts.append(json.dumps(result, indent=2, default=str))
                
                # Handle schema
                elif step.tool_name and 'schema' in step.tool_name.lower():
                    tables = result.get('tables', [])
                    summary_parts.append(f"DATABASE SCHEMA: {len(tables)} tables found")
                    for table in tables[:5]:
                        summary_parts.append(f"  • {table.get('name', 'unknown')}: {len(table.get('columns', []))} columns")
                
                # Default handling for other tools
                else:
                    if isinstance(result, dict):
                        if 'error' in result:
                            summary_parts.append(f"ERROR: {result['error']}")
                        else:
                            summary_parts.append(json.dumps(result, indent=2, default=str))
                    elif isinstance(result, list):
                        summary_parts.append(f"Results: {len(result)} records")
                        if result:
                            summary_parts.append(f"Sample: {result[:3]}")
                    else:
                        summary_parts.append(str(result))
                
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
        """Extract actual data and metrics from completed investigation steps"""
        if not self.current_investigation:
            return "No metrics available from completed steps."
        
        metrics = []
        visualizations_data = []
        
        for step in self.current_investigation:
            if step.step_type == "tool_call" and step.result:
                # Get actual data - handle both old and new structure
                data = step.result.get('data', step.result) if isinstance(step.result, dict) else step.result
                
                if not data:
                    continue
                
                # Extract from visualization tools
                if step.tool_name in ['generate_bar_chart', 'generate_line_chart', 'generate_pie_chart', 'generate_scatter_plot']:
                    chart_data = step.result.get('chart_data', {})
                    if chart_data:
                        # Extract labels and values from chart data
                        if 'labels' in chart_data and 'values' in chart_data:
                            viz_summary = [f"\n**{step.result.get('title', step.tool_name)}:**"]
                            labels = chart_data['labels']
                            values = chart_data['values']
                            for label, value in zip(labels[:10], values[:10]):  # Limit to 10 rows
                                if isinstance(value, (int, float)):
                                    viz_summary.append(f"  - {label}: ${value:,.2f}" if 'revenue' in str(step.description).lower() else f"  - {label}: {value:,.0f}")
                                else:
                                    viz_summary.append(f"  - {label}: {value}")
                            visualizations_data.append("\n".join(viz_summary))
                        
                        # For datasets (line charts)
                        if 'datasets' in chart_data:
                            viz_summary = [f"\n**{step.result.get('title', step.tool_name)}:**"]
                            datasets = chart_data['datasets']
                            for ds in datasets[:5]:  # Limit to 5 datasets
                                ds_name = ds.get('label', 'Dataset')
                                ds_values = ds.get('data', [])
                                if ds_values:
                                    total = sum(v for v in ds_values if isinstance(v, (int, float)))
                                    viz_summary.append(f"  - {ds_name}: Total ${total:,.2f}" if 'revenue' in str(step.description).lower() else f"  - {ds_name}: {total:,.0f}")
                            visualizations_data.append("\n".join(viz_summary))
                
                # Extract metrics from SQL query results
                elif isinstance(data, list) and len(data) > 0:
                    if step.tool_name == 'execute_sql_query':
                        # Show first few rows of results
                        metrics.append(f"\n**SQL Query Results ({len(data)} rows):**")
                        for row in data[:5]:  # Limit to 5 rows
                            if isinstance(row, dict):
                                row_str = ", ".join(f"{k}: {v:,.2f}" if isinstance(v, (int, float)) else f"{k}: {v}" for k, v in row.items())
                                metrics.append(f"  - {row_str}")
                    else:
                        metrics.append(f"- {step.tool_name}: {len(data)} records analyzed")
                
                # Extract table information
                elif isinstance(data, dict):
                    if 'tables' in data:  # Schema information
                        table_count = len(data['tables'])
                        table_names = [t.get('name', 'unknown') for t in data['tables'][:5]]
                        metrics.append(f"- Database contains {table_count} tables: {', '.join(table_names)}")
                    
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
                    
                    # Extract comparison results
                    if 'period1_total' in data:
                        metrics.append(f"\n**Time Period Comparison:**")
                        metrics.append(f"  - Period 1 Total: ${data.get('period1_total', 0):,.2f}")
                        metrics.append(f"  - Period 2 Total: ${data.get('period2_total', 0):,.2f}")
                        metrics.append(f"  - Change: {data.get('percent_change', 0):.1f}%")
        
        # Combine metrics and visualization data
        all_content = []
        if visualizations_data:
            all_content.append("**Data from Visualizations:**")
            all_content.extend(visualizations_data)
        if metrics:
            all_content.append("\n**Additional Metrics:**")
            all_content.extend(metrics)
        
        return "\n".join(all_content) if all_content else "- Investigation in progress, metrics will be available upon completion"
    
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
    
    def save_to_memory(self, user_query: str) -> None:
        """Save the current investigation to conversation memory"""
        if not self.current_investigation:
            return
        
        # Extract key information from investigation
        tool_calls = [step for step in self.current_investigation if step.step_type == "tool_call"]
        conclusions = [step for step in self.current_investigation if step.step_type == "conclusion"]
        
        # Get tools used
        tools_used = list(set(step.tool_name for step in tool_calls if step.tool_name))
        
        # Get any SQL that was generated
        sql_generated = None
        for step in tool_calls:
            if step.tool_name == "execute_sql_query" and step.parameters:
                sql_generated = step.parameters.get("query", step.parameters.get("sql"))
                break
        
        # Get visualization type
        visualization_type = None
        for step in tool_calls:
            if step.tool_name and "chart" in step.tool_name.lower():
                visualization_type = step.tool_name
                break
        
        # Get conclusion/response
        assistant_response = ""
        if conclusions:
            last_conclusion = conclusions[-1]
            if last_conclusion.result and isinstance(last_conclusion.result, dict):
                assistant_response = last_conclusion.result.get("analysis", "")
        
        # Build results summary
        results_summary = {
            "total_steps": len(self.current_investigation),
            "tools_executed": len(tool_calls),
            "tools_list": tools_used[:5]  # Limit to first 5
        }
        
        # Add any numeric results we can extract
        for step in tool_calls:
            if step.result and isinstance(step.result, dict):
                data = step.result.get("data", {})
                if isinstance(data, dict):
                    if "row_count" in data:
                        results_summary["row_count"] = data["row_count"]
                    if "total" in data:
                        results_summary["total"] = data["total"]
        
        # Save to memory
        self.memory.add_exchange(
            user_query=user_query,
            assistant_response=assistant_response[:1000] if assistant_response else "Investigation completed",
            sql_generated=sql_generated,
            results_summary=results_summary,
            visualization_type=visualization_type,
            tools_used=tools_used
        )
        
        logger.info(f"💾 Saved investigation to memory. Buffer: {len(self.memory.exchanges)}/{self.memory.max_exchanges}")