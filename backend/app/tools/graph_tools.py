"""
Specific graph generation tools - one for each chart type
"""

import json
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool, ToolParameter, ToolResult


class GenerateBarChartTool(BaseTool):
    """Generate bar chart for categorical data comparison"""
    
    @property
    def name(self) -> str:
        return "generate_bar_chart"
    
    @property
    def description(self) -> str:
        return "Generate a bar chart to compare values across categories. Perfect for sales by product, revenue by region, etc."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql_query",
                type="string",
                description="SQL query to get data for the bar chart (should return category and value columns)",
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Chart title",
                required=True
            ),
            ToolParameter(
                name="x_label",
                type="string",
                description="X-axis label (category)",
                required=True
            ),
            ToolParameter(
                name="y_label",
                type="string",
                description="Y-axis label (value)",
                required=True
            )
        ]
    
    async def execute(self, sql_query: str, title: str, x_label: str, y_label: str) -> ToolResult:
        """Generate bar chart by executing SQL and creating chart config"""
        try:
            # Execute SQL query using the safe execute_query method
            results = await self.db_manager.execute_query(sql_query)
            
            if not results:
                return ToolResult(
                    success=False,
                    error="SQL query returned no data for bar chart",
                    execution_time_ms=0
                )
            
            # Results are already list of dicts from execute_query
            data = results
            
            # Create chart configuration
            chart_config = {
                "type": "bar",
                "title": title,
                "data": data,
                "config": {
                    "x_field": list(data[0].keys())[0] if data else "category",
                    "y_field": list(data[0].keys())[1] if len(data[0].keys()) > 1 else "value",
                    "x_label": x_label,
                    "y_label": y_label
                },
                "sql_query": sql_query,
                "data_points": len(data)
            }
            
            return ToolResult(
                success=True,
                data=chart_config,
                execution_time_ms=100,
                metadata={
                    "chart_type": "bar",
                    "data_points": len(data),
                    "sql_executed": True
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error generating bar chart: {str(e)}",
                execution_time_ms=0
            )


class GenerateLineChartTool(BaseTool):
    """Generate line chart for time series and trend data"""
    
    @property
    def name(self) -> str:
        return "generate_line_chart"
    
    @property
    def description(self) -> str:
        return "Generate a line chart to show trends over time. Perfect for sales trends, monthly revenue, etc."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql_query",
                type="string",
                description="SQL query to get time series data (should return time/date and value columns)",
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Chart title",
                required=True
            ),
            ToolParameter(
                name="x_label",
                type="string",
                description="X-axis label (time/date)",
                required=True
            ),
            ToolParameter(
                name="y_label",
                type="string",
                description="Y-axis label (value)",
                required=True
            )
        ]
    
    async def execute(self, sql_query: str, title: str, x_label: str, y_label: str) -> ToolResult:
        """Generate line chart by executing SQL and creating chart config"""
        try:
            # Execute SQL query using the safe execute_query method
            results = await self.db_manager.execute_query(sql_query)
            
            if not results:
                return ToolResult(
                    success=False,
                    error="SQL query returned no data for line chart",
                    execution_time_ms=0
                )
            
            # Results are already list of dicts from execute_query
            data = results
            
            # Create chart configuration
            chart_config = {
                "type": "line",
                "title": title,
                "data": data,
                "config": {
                    "x_field": list(data[0].keys())[0] if data else "time",
                    "y_field": list(data[0].keys())[1] if len(data[0].keys()) > 1 else "value",
                    "x_label": x_label,
                    "y_label": y_label
                },
                "sql_query": sql_query,
                "data_points": len(data)
            }
            
            return ToolResult(
                success=True,
                data=chart_config,
                execution_time_ms=100,
                metadata={
                    "chart_type": "line",
                    "data_points": len(data),
                    "sql_executed": True
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error generating line chart: {str(e)}",
                execution_time_ms=0
            )


class GeneratePieChartTool(BaseTool):
    """Generate pie chart for showing proportional data"""
    
    @property
    def name(self) -> str:
        return "generate_pie_chart"
    
    @property
    def description(self) -> str:
        return "Generate a pie chart to show proportional distribution. Perfect for market share, sales by category, etc."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql_query",
                type="string",
                description="SQL query to get proportional data (should return category and value columns)",
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Chart title",
                required=True
            )
        ]
    
    async def execute(self, sql_query: str, title: str) -> ToolResult:
        """Generate pie chart by executing SQL and creating chart config"""
        try:
            # Execute SQL query using the safe execute_query method
            results = await self.db_manager.execute_query(sql_query)
            
            if not results:
                return ToolResult(
                    success=False,
                    error="SQL query returned no data for pie chart",
                    execution_time_ms=0
                )
            
            # Results are already list of dicts from execute_query
            data = results
            
            # Create chart configuration
            chart_config = {
                "type": "pie",
                "title": title,
                "data": data,
                "config": {
                    "label_field": list(data[0].keys())[0] if data else "category",
                    "value_field": list(data[0].keys())[1] if len(data[0].keys()) > 1 else "value"
                },
                "sql_query": sql_query,
                "data_points": len(data)
            }
            
            return ToolResult(
                success=True,
                data=chart_config,
                execution_time_ms=100,
                metadata={
                    "chart_type": "pie",
                    "data_points": len(data),
                    "sql_executed": True
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error generating pie chart: {str(e)}",
                execution_time_ms=0
            )


class GenerateScatterPlotTool(BaseTool):
    """Generate scatter plot for correlation analysis"""
    
    @property
    def name(self) -> str:
        return "generate_scatter_plot"
    
    @property
    def description(self) -> str:
        return "Generate a scatter plot to show correlation between two numeric variables. Perfect for price vs sales, quantity vs revenue, etc."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql_query",
                type="string",
                description="SQL query to get correlation data (should return two numeric columns)",
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Chart title",
                required=True
            ),
            ToolParameter(
                name="x_label",
                type="string",
                description="X-axis label",
                required=True
            ),
            ToolParameter(
                name="y_label",
                type="string",
                description="Y-axis label",
                required=True
            )
        ]
    
    async def execute(self, sql_query: str, title: str, x_label: str, y_label: str) -> ToolResult:
        """Generate scatter plot by executing SQL and creating chart config"""
        try:
            # Execute SQL query using the safe execute_query method
            results = await self.db_manager.execute_query(sql_query)
            
            if not results:
                return ToolResult(
                    success=False,
                    error="SQL query returned no data for scatter plot",
                    execution_time_ms=0
                )
            
            # Results are already list of dicts from execute_query
            data = results
            
            # Create chart configuration
            chart_config = {
                "type": "scatter",
                "title": title,
                "data": data,
                "config": {
                    "x_field": list(data[0].keys())[0] if data else "x",
                    "y_field": list(data[0].keys())[1] if len(data[0].keys()) > 1 else "y",
                    "x_label": x_label,
                    "y_label": y_label
                },
                "sql_query": sql_query,
                "data_points": len(data)
            }
            
            return ToolResult(
                success=True,
                data=chart_config,
                execution_time_ms=100,
                metadata={
                    "chart_type": "scatter",
                    "data_points": len(data),
                    "sql_executed": True
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error generating scatter plot: {str(e)}",
                execution_time_ms=0
            )



