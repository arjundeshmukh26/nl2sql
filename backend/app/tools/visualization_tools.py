"""
Visualization and chart generation tools - completely general purpose
"""

import json
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool, ToolParameter, ToolResult


class GenerateChartTool(BaseTool):
    """Generate chart configuration for data visualization"""
    
    @property
    def name(self) -> str:
        return "generate_chart"
    
    @property
    def description(self) -> str:
        return "Generate chart configuration for visualizing data. Supports bar charts, line charts, pie charts, scatter plots, and more."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="data",
                type="string",
                description="JSON string of data objects to visualize (will be parsed as array)",
                required=True
            ),
            ToolParameter(
                name="chart_type",
                type="string",
                description="Type of chart to generate",
                required=True,
                enum_values=["bar", "line", "pie", "scatter", "area", "column", "donut"]
            ),
            ToolParameter(
                name="x_field",
                type="string",
                description="Field name for X-axis (required for bar, line, scatter, area charts)",
                required=False
            ),
            ToolParameter(
                name="y_field",
                type="string",
                description="Field name for Y-axis (required for bar, line, scatter, area charts)",
                required=False
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Chart title",
                required=False
            ),
            ToolParameter(
                name="x_label",
                type="string",
                description="X-axis label",
                required=False
            ),
            ToolParameter(
                name="y_label",
                type="string",
                description="Y-axis label",
                required=False
            )
        ]
    
    async def execute(self, data: str, chart_type: str, x_field: str = None, 
                     y_field: str = None, title: str = None, x_label: str = None, 
                     y_label: str = None) -> ToolResult:
        """Generate chart configuration"""
        try:
            # Parse JSON string to list
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return ToolResult(
                        success=False,
                        error="Invalid JSON format for data parameter",
                        execution_time_ms=0
                    )
            
            if not data or len(data) == 0:
                return ToolResult(
                    success=False,
                    error="No data provided for visualization",
                    execution_time_ms=0
                )
            
            # Validate required fields for different chart types
            if chart_type in ["bar", "line", "scatter", "area", "column"]:
                if not x_field or not y_field:
                    return ToolResult(
                        success=False,
                        error=f"Chart type '{chart_type}' requires both x_field and y_field parameters",
                        execution_time_ms=0
                    )
                
                # Validate fields exist in data
                if x_field not in data[0] or y_field not in data[0]:
                    available_fields = list(data[0].keys()) if data else []
                    return ToolResult(
                        success=False,
                        error=f"Fields '{x_field}' or '{y_field}' not found in data. Available fields: {available_fields}",
                        execution_time_ms=0
                    )
            
            elif chart_type in ["pie", "donut"]:
                if not x_field or not y_field:
                    return ToolResult(
                        success=False,
                        error=f"Chart type '{chart_type}' requires x_field (labels) and y_field (values) parameters",
                        execution_time_ms=0
                    )
            
            # Generate chart configuration
            chart_config = {
                "type": chart_type,
                "data": data,
                "config": {
                    "x_field": x_field,
                    "y_field": y_field,
                    "title": title or f"{chart_type.title()} Chart",
                    "x_label": x_label or x_field,
                    "y_label": y_label or y_field
                },
                "metadata": {
                    "data_points": len(data),
                    "chart_type": chart_type,
                    "generated_at": "now"
                }
            }
            
            return ToolResult(
                success=True,
                data=chart_config,
                execution_time_ms=50,
                metadata={
                    "chart_type": chart_type,
                    "data_points": len(data)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error generating chart: {str(e)}",
                execution_time_ms=0
            )


class SuggestVisualizationTool(BaseTool):
    """Suggest appropriate visualization types for given data"""
    
    @property
    def name(self) -> str:
        return "suggest_visualization"
    
    @property
    def description(self) -> str:
        return "Analyze data structure and suggest the most appropriate visualization types and configurations."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="data",
                type="string",
                description="JSON string of data objects to analyze for visualization suggestions",
                required=True
            ),
            ToolParameter(
                name="analysis_goal",
                type="string",
                description="What you want to show with the visualization (trends, comparisons, distributions, etc.)",
                required=False
            )
        ]
    
    async def execute(self, data: str, analysis_goal: str = None) -> ToolResult:
        """Suggest appropriate visualizations for the data"""
        try:
            # Parse JSON string to list
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return ToolResult(
                        success=False,
                        error="Invalid JSON format for data parameter",
                        execution_time_ms=0
                    )
            
            if not data or len(data) == 0:
                return ToolResult(
                    success=False,
                    error="No data provided for analysis",
                    execution_time_ms=0
                )
            
            # Analyze data structure
            sample_record = data[0]
            fields = list(sample_record.keys())
            
            suggestions = []
            
            # Analyze field types
            numeric_fields = []
            categorical_fields = []
            date_fields = []
            
            for field in fields:
                sample_value = sample_record[field]
                if isinstance(sample_value, (int, float)):
                    numeric_fields.append(field)
                elif isinstance(sample_value, str):
                    # Check if it might be a date
                    if any(date_word in field.lower() for date_word in ['date', 'time', 'created', 'updated']):
                        date_fields.append(field)
                    else:
                        categorical_fields.append(field)
            
            # Generate suggestions based on data structure
            if len(numeric_fields) >= 2:
                suggestions.append({
                    "chart_type": "scatter",
                    "x_field": numeric_fields[0],
                    "y_field": numeric_fields[1],
                    "title": f"{numeric_fields[1]} vs {numeric_fields[0]}",
                    "use_case": "Show correlation between two numeric variables"
                })
            
            if len(categorical_fields) >= 1 and len(numeric_fields) >= 1:
                suggestions.append({
                    "chart_type": "bar",
                    "x_field": categorical_fields[0],
                    "y_field": numeric_fields[0],
                    "title": f"{numeric_fields[0]} by {categorical_fields[0]}",
                    "use_case": "Compare values across categories"
                })
                
                suggestions.append({
                    "chart_type": "pie",
                    "x_field": categorical_fields[0],
                    "y_field": numeric_fields[0],
                    "title": f"Distribution of {numeric_fields[0]}",
                    "use_case": "Show proportional distribution"
                })
            
            if len(date_fields) >= 1 and len(numeric_fields) >= 1:
                suggestions.append({
                    "chart_type": "line",
                    "x_field": date_fields[0],
                    "y_field": numeric_fields[0],
                    "title": f"{numeric_fields[0]} over time",
                    "use_case": "Show trends over time"
                })
            
            # Add analysis goal specific suggestions
            if analysis_goal:
                goal_lower = analysis_goal.lower()
                if "trend" in goal_lower and date_fields and numeric_fields:
                    suggestions.insert(0, {
                        "chart_type": "line",
                        "x_field": date_fields[0],
                        "y_field": numeric_fields[0],
                        "title": f"{numeric_fields[0]} Trend",
                        "use_case": "Perfect for trend analysis"
                    })
                elif "comparison" in goal_lower and categorical_fields and numeric_fields:
                    suggestions.insert(0, {
                        "chart_type": "bar",
                        "x_field": categorical_fields[0],
                        "y_field": numeric_fields[0],
                        "title": f"Comparison by {categorical_fields[0]}",
                        "use_case": "Ideal for comparisons"
                    })
            
            result = {
                "data_analysis": {
                    "total_records": len(data),
                    "fields": fields,
                    "numeric_fields": numeric_fields,
                    "categorical_fields": categorical_fields,
                    "date_fields": date_fields
                },
                "visualization_suggestions": suggestions,
                "recommended": suggestions[0] if suggestions else None
            }
            
            return ToolResult(
                success=True,
                data=result,
                execution_time_ms=100,
                metadata={
                    "suggestions_count": len(suggestions),
                    "analysis_goal": analysis_goal
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error analyzing data for visualization: {str(e)}",
                execution_time_ms=0
            )
