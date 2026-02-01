"""
Tool registry and execution system for agentic database investigation
"""

from typing import Dict, List, Any, Optional
import json
import time
from .base_tool import BaseTool, ToolResult

# Import all tool classes
from .database_tools import (
    GetDatabaseSchemaTool,
    DescribeTableTool,
    GetTableSampleDataTool,
    EstimateTableSizeTool
)
from .sql_execution_tools import (
    ExecuteSQLQueryTool,
    ValidateSQLSyntaxTool,
    ExplainQueryPlanTool,
    OptimizeQueryTool
)
from .analysis_tools import (
    GetColumnStatisticsTool,
    DetectDataAnomaliesTool,
    FindCorrelationsTool,
    AnalyzeDataQualityTool
)
from .investigation_tools import (
    GenerateDrillDownQueriesTool,
    CompareTimePeriodsTool,
    DetectSeasonalPatternsTool
)
from .visualization_tools import (
    GenerateChartTool,
    SuggestVisualizationTool
)
from .graph_tools import (
    GenerateBarChartTool,
    GenerateLineChartTool,
    GeneratePieChartTool,
    GenerateScatterPlotTool
)
from .business_metrics_tools import (
    GetKeyBusinessMetricsTool,
    GenerateBusinessSummaryTool
)
from .anomaly_detection_tools import (
    DetectRevenueAnomalies,
    DetectTimePatternAnomalies,
    DetectCustomerBehaviorAnomalies
)


class ToolRegistry:
    """Registry for all available agentic database tools"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.tools: Dict[str, BaseTool] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools"""
        
        # Database discovery tools
        self.register_tool(GetDatabaseSchemaTool(self.db_manager))
        self.register_tool(DescribeTableTool(self.db_manager))
        self.register_tool(GetTableSampleDataTool(self.db_manager))
        self.register_tool(EstimateTableSizeTool(self.db_manager))
        
        # SQL execution tools
        self.register_tool(ExecuteSQLQueryTool(self.db_manager))
        self.register_tool(ValidateSQLSyntaxTool(self.db_manager))
        self.register_tool(ExplainQueryPlanTool(self.db_manager))
        self.register_tool(OptimizeQueryTool(self.db_manager))
        
        # Analysis tools
        self.register_tool(GetColumnStatisticsTool(self.db_manager))
        self.register_tool(DetectDataAnomaliesTool(self.db_manager))
        self.register_tool(FindCorrelationsTool(self.db_manager))
        self.register_tool(AnalyzeDataQualityTool(self.db_manager))
        
        # Investigation tools
        self.register_tool(GenerateDrillDownQueriesTool(self.db_manager))
        self.register_tool(CompareTimePeriodsTool(self.db_manager))
        self.register_tool(DetectSeasonalPatternsTool(self.db_manager))
        
        # Visualization tools
        self.register_tool(GenerateChartTool(self.db_manager))
        self.register_tool(SuggestVisualizationTool(self.db_manager))
        
        # Specific graph tools
        self.register_tool(GenerateBarChartTool(self.db_manager))
        self.register_tool(GenerateLineChartTool(self.db_manager))
        self.register_tool(GeneratePieChartTool(self.db_manager))
        self.register_tool(GenerateScatterPlotTool(self.db_manager))
        
        # Business metrics tools
        self.register_tool(GetKeyBusinessMetricsTool(self.db_manager))
        self.register_tool(GenerateBusinessSummaryTool(self.db_manager))
        
        # Anomaly detection tools
        self.register_tool(DetectRevenueAnomalies(self.db_manager))
        self.register_tool(DetectTimePatternAnomalies(self.db_manager))
        self.register_tool(DetectCustomerBehaviorAnomalies(self.db_manager))
    
    def register_tool(self, tool: BaseTool):
        """Register a tool in the registry"""
        self.tools[tool.name] = tool
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """Get list of all available tool names"""
        return list(self.tools.keys())
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling definitions for all tools"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """Get tools organized by category"""
        categories = {
            "database_discovery": [
                "get_database_schema",
                "describe_table", 
                "get_table_sample_data",
                "estimate_table_size"
            ],
            "sql_execution": [
                "execute_sql_query",
                "validate_sql_syntax",
                "explain_query_plan",
                "optimize_query"
            ],
            "data_analysis": [
                "get_column_statistics",
                "detect_data_anomalies",
                "find_correlations",
                "analyze_data_quality"
            ],
            "investigation": [
                "generate_drill_down_queries",
                "compare_time_periods", 
                "detect_seasonal_patterns"
            ],
            "visualization": [
                "generate_chart",
                "suggest_visualization"
            ],
            "graphs": [
                "generate_bar_chart",
                "generate_line_chart", 
                "generate_pie_chart",
                "generate_scatter_plot"
            ],
            "business_metrics": [
                "get_key_business_metrics",
                "generate_business_summary"
            ],
            "anomaly_detection": [
                "detect_revenue_anomalies",
                "detect_time_pattern_anomalies", 
                "detect_customer_behavior_anomalies"
            ]
        }
        return categories
    
    async def execute_tool(self, tool_name: str, **parameters) -> ToolResult:
        """Execute a tool with given parameters"""
        tool = self.get_tool(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found. Available tools: {', '.join(self.list_tools())}"
            )
        
        # Record execution start
        execution_record = {
            "tool_name": tool_name,
            "parameters": parameters,
            "start_time": time.time(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Execute tool
            result = await tool.safe_execute(**parameters)
            
            # Record execution completion
            execution_record.update({
                "end_time": time.time(),
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error if not result.success else None
            })
            
            self.execution_history.append(execution_record)
            
            return result
            
        except Exception as e:
            execution_record.update({
                "end_time": time.time(),
                "success": False,
                "error": str(e)
            })
            
            self.execution_history.append(execution_record)
            
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )
    
    def get_execution_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get tool execution history"""
        history = self.execution_history
        if limit:
            history = history[-limit:]
        return history
    
    def get_tool_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about tool usage"""
        if not self.execution_history:
            return {"message": "No tool executions recorded"}
        
        # Count executions by tool
        tool_counts = {}
        successful_executions = 0
        total_execution_time = 0
        
        for execution in self.execution_history:
            tool_name = execution["tool_name"]
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            
            if execution["success"]:
                successful_executions += 1
            
            if execution.get("execution_time_ms"):
                total_execution_time += execution["execution_time_ms"]
        
        return {
            "total_executions": len(self.execution_history),
            "successful_executions": successful_executions,
            "success_rate": round(successful_executions / len(self.execution_history) * 100, 2),
            "total_execution_time_ms": total_execution_time,
            "average_execution_time_ms": round(total_execution_time / len(self.execution_history), 2),
            "tool_usage_counts": tool_counts,
            "most_used_tool": max(tool_counts.items(), key=lambda x: x[1]) if tool_counts else None
        }
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history = []
    
    def get_tool_help(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get help information for tools"""
        if tool_name:
            tool = self.get_tool(tool_name)
            if not tool:
                return {"error": f"Tool '{tool_name}' not found"}
            
            return {
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": param.name,
                        "type": param.type,
                        "description": param.description,
                        "required": param.required,
                        "default": param.default,
                        "enum_values": param.enum_values
                    }
                    for param in tool.parameters
                ],
                "example_usage": f"Use this tool to {tool.description.lower()}"
            }
        else:
            # Return overview of all tools
            categories = self.get_tools_by_category()
            return {
                "total_tools": len(self.tools),
                "categories": {
                    category: {
                        "tools": tool_names,
                        "descriptions": {
                            tool_name: self.get_tool(tool_name).description 
                            for tool_name in tool_names
                        }
                    }
                    for category, tool_names in categories.items()
                }
            }


# Global tool registry instance
_tool_registry = None

def get_tool_registry(db_manager=None) -> ToolRegistry:
    """Get the global tool registry instance"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry(db_manager)
    return _tool_registry

def initialize_tools(db_manager):
    """Initialize the tool registry with database manager"""
    global _tool_registry
    _tool_registry = ToolRegistry(db_manager)
    return _tool_registry
