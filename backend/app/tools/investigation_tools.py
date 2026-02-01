"""
Autonomous investigation and hypothesis testing tools
"""

from typing import List, Dict, Any, Optional
from .base_tool import BaseTool, ToolParameter, ToolResult
import json


class GenerateDrillDownQueriesTool(BaseTool):
    """Generate follow-up queries based on initial results"""
    
    @property
    def name(self) -> str:
        return "generate_drill_down_queries"
    
    @property
    def description(self) -> str:
        return "Generate follow-up SQL queries to drill down into specific findings or investigate patterns deeper. Use this to create targeted queries based on initial analysis results."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="base_table",
                type="string",
                description="The main table being investigated"
            ),
            ToolParameter(
                name="finding_description",
                type="string",
                description="Description of the finding that needs deeper investigation"
            ),
            ToolParameter(
                name="dimension_column",
                type="string",
                description="Column to drill down by (e.g., region, product, time period)"
            ),
            ToolParameter(
                name="metric_column",
                type="string",
                description="The metric column being analyzed (e.g., revenue, count, average)"
            ),
            ToolParameter(
                name="filter_conditions",
                type="string",
                description="Optional WHERE conditions to focus the drill-down",
                required=False
            )
        ]
    
    async def execute(self, base_table: str, finding_description: str, dimension_column: str, metric_column: str, filter_conditions: Optional[str] = None) -> ToolResult:
        """Generate drill-down queries"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Get table schema to understand available columns
            schema_query = """
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position
            """
            
            columns = await conn.fetch(schema_query, base_table)
            available_columns = {col['column_name']: col['data_type'] for col in columns}
            
            if dimension_column not in available_columns:
                return ToolResult(
                    success=False,
                    error=f"Dimension column '{dimension_column}' not found in table '{base_table}'"
                )
            
            if metric_column not in available_columns:
                return ToolResult(
                    success=False,
                    error=f"Metric column '{metric_column}' not found in table '{base_table}'"
                )
            
            # Generate different types of drill-down queries
            drill_down_queries = []
            
            # 1. Basic breakdown by dimension
            base_where = f"WHERE {filter_conditions}" if filter_conditions else ""
            
            basic_query = f"""
                SELECT 
                    {dimension_column},
                    COUNT(*) as record_count,
                    SUM({metric_column}) as total_{metric_column},
                    AVG({metric_column}) as avg_{metric_column},
                    MIN({metric_column}) as min_{metric_column},
                    MAX({metric_column}) as max_{metric_column}
                FROM {base_table}
                {base_where}
                GROUP BY {dimension_column}
                ORDER BY total_{metric_column} DESC
            """
            
            drill_down_queries.append({
                "type": "basic_breakdown",
                "description": f"Breakdown of {metric_column} by {dimension_column}",
                "sql": basic_query,
                "purpose": "See how the metric varies across different values of the dimension"
            })
            
            # 2. Top and bottom performers
            top_bottom_query = f"""
                (SELECT 
                    {dimension_column},
                    SUM({metric_column}) as total_{metric_column},
                    'top_performer' as category
                FROM {base_table}
                {base_where}
                GROUP BY {dimension_column}
                ORDER BY total_{metric_column} DESC
                LIMIT 5)
                UNION ALL
                (SELECT 
                    {dimension_column},
                    SUM({metric_column}) as total_{metric_column},
                    'bottom_performer' as category
                FROM {base_table}
                {base_where}
                GROUP BY {dimension_column}
                ORDER BY total_{metric_column} ASC
                LIMIT 5)
                ORDER BY total_{metric_column} DESC
            """
            
            drill_down_queries.append({
                "type": "top_bottom_analysis",
                "description": f"Top 5 and bottom 5 {dimension_column} by {metric_column}",
                "sql": top_bottom_query,
                "purpose": "Identify best and worst performing segments"
            })
            
            # 3. Statistical outliers within dimension
            outlier_query = f"""
                WITH stats AS (
                    SELECT 
                        {dimension_column},
                        AVG({metric_column}) as avg_metric,
                        STDDEV({metric_column}) as std_metric
                    FROM {base_table}
                    {base_where}
                    GROUP BY {dimension_column}
                ),
                outliers AS (
                    SELECT 
                        s.*,
                        ABS(avg_metric - (SELECT AVG(avg_metric) FROM stats)) / 
                        NULLIF((SELECT STDDEV(avg_metric) FROM stats), 0) as z_score
                    FROM stats s
                )
                SELECT 
                    {dimension_column},
                    avg_metric,
                    z_score,
                    CASE 
                        WHEN z_score > 2 THEN 'high_outlier'
                        WHEN z_score < -2 THEN 'low_outlier'
                        ELSE 'normal'
                    END as outlier_type
                FROM outliers
                WHERE ABS(z_score) > 1.5
                ORDER BY ABS(z_score) DESC
            """
            
            drill_down_queries.append({
                "type": "outlier_detection",
                "description": f"Statistical outliers in {metric_column} by {dimension_column}",
                "sql": outlier_query,
                "purpose": "Find unusual patterns that deviate from the norm"
            })
            
            # 4. Time-based analysis (if date columns exist)
            date_columns = [col for col, dtype in available_columns.items() 
                          if dtype in ['date', 'timestamp', 'timestamp with time zone']]
            
            if date_columns:
                date_col = date_columns[0]  # Use first date column
                
                time_trend_query = f"""
                    SELECT 
                        DATE_TRUNC('month', {date_col}) as time_period,
                        {dimension_column},
                        SUM({metric_column}) as total_{metric_column},
                        COUNT(*) as record_count
                    FROM {base_table}
                    {base_where}
                    GROUP BY DATE_TRUNC('month', {date_col}), {dimension_column}
                    ORDER BY time_period DESC, total_{metric_column} DESC
                """
                
                drill_down_queries.append({
                    "type": "time_trend_analysis",
                    "description": f"Monthly trend of {metric_column} by {dimension_column}",
                    "sql": time_trend_query,
                    "purpose": "Understand how patterns change over time"
                })
            
            # 5. Comparative analysis with overall average
            comparative_query = f"""
                WITH overall_stats AS (
                    SELECT AVG({metric_column}) as overall_avg
                    FROM {base_table}
                    {base_where}
                ),
                dimension_stats AS (
                    SELECT 
                        {dimension_column},
                        AVG({metric_column}) as dimension_avg,
                        COUNT(*) as record_count
                    FROM {base_table}
                    {base_where}
                    GROUP BY {dimension_column}
                )
                SELECT 
                    ds.{dimension_column},
                    ds.dimension_avg,
                    os.overall_avg,
                    ds.dimension_avg - os.overall_avg as difference_from_avg,
                    ROUND((ds.dimension_avg - os.overall_avg) / os.overall_avg * 100, 2) as percentage_difference,
                    ds.record_count
                FROM dimension_stats ds
                CROSS JOIN overall_stats os
                ORDER BY ABS(ds.dimension_avg - os.overall_avg) DESC
            """
            
            drill_down_queries.append({
                "type": "comparative_analysis",
                "description": f"Compare {dimension_column} performance against overall average",
                "sql": comparative_query,
                "purpose": "Identify which segments perform above or below average"
            })
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data={
                    "base_table": base_table,
                    "finding_description": finding_description,
                    "dimension_column": dimension_column,
                    "metric_column": metric_column,
                    "filter_conditions": filter_conditions,
                    "drill_down_queries": drill_down_queries,
                    "available_columns": list(available_columns.keys())
                },
                metadata={
                    "queries_generated": len(drill_down_queries),
                    "has_time_analysis": any(q["type"] == "time_trend_analysis" for q in drill_down_queries)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CompareTimePeriodsTool(BaseTool):
    """Compare metrics between different time periods"""
    
    @property
    def name(self) -> str:
        return "compare_time_periods"
    
    @property
    def description(self) -> str:
        return "Compare metrics between different time periods to identify trends, seasonal patterns, and performance changes. Essential for temporal analysis."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table containing time-series data"
            ),
            ToolParameter(
                name="date_column",
                type="string",
                description="Name of the date/timestamp column"
            ),
            ToolParameter(
                name="metric_column",
                type="string",
                description="Name of the metric column to compare"
            ),
            ToolParameter(
                name="period1_start",
                type="string",
                description="Start date of first period (YYYY-MM-DD format)"
            ),
            ToolParameter(
                name="period1_end",
                type="string",
                description="End date of first period (YYYY-MM-DD format)"
            ),
            ToolParameter(
                name="period2_start",
                type="string",
                description="Start date of second period (YYYY-MM-DD format)"
            ),
            ToolParameter(
                name="period2_end",
                type="string",
                description="End date of second period (YYYY-MM-DD format)"
            ),
            ToolParameter(
                name="group_by_column",
                type="string",
                description="Optional column to group by (e.g., region, product)",
                required=False
            )
        ]
    
    async def execute(self, table_name: str, date_column: str, metric_column: str, 
                     period1_start: str, period1_end: str, period2_start: str, period2_end: str,
                     group_by_column: Optional[str] = None) -> ToolResult:
        """Compare metrics between time periods"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Validate columns exist
            columns_query = """
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = $1
            """
            
            columns = await conn.fetch(columns_query, table_name)
            available_columns = {col['column_name']: col['data_type'] for col in columns}
            
            if date_column not in available_columns:
                return ToolResult(success=False, error=f"Date column '{date_column}' not found")
            
            if metric_column not in available_columns:
                return ToolResult(success=False, error=f"Metric column '{metric_column}' not found")
            
            if group_by_column and group_by_column not in available_columns:
                return ToolResult(success=False, error=f"Group by column '{group_by_column}' not found")
            
            # Build comparison query with proper table aliases
            # Use explicit alias for group_by_column to avoid ambiguity
            group_select_p1 = f"t.{group_by_column} as group_key, " if group_by_column else ""
            group_select_p2 = f"t.{group_by_column} as group_key, " if group_by_column else ""
            group_by_sql = f"GROUP BY t.{group_by_column}" if group_by_column else ""
            
            comparison_query = f"""
                WITH period1_data AS (
                    SELECT 
                        {group_select_p1}
                        SUM(t.{metric_column}) as period1_total,
                        AVG(t.{metric_column}) as period1_avg,
                        COUNT(*) as period1_count,
                        MIN(t.{metric_column}) as period1_min,
                        MAX(t.{metric_column}) as period1_max
                    FROM {table_name} t
                    WHERE t.{date_column} >= '{period1_start}' 
                    AND t.{date_column} <= '{period1_end}'
                    AND t.{metric_column} IS NOT NULL
                    {group_by_sql}
                ),
                period2_data AS (
                    SELECT 
                        {group_select_p2}
                        SUM(t.{metric_column}) as period2_total,
                        AVG(t.{metric_column}) as period2_avg,
                        COUNT(*) as period2_count,
                        MIN(t.{metric_column}) as period2_min,
                        MAX(t.{metric_column}) as period2_max
                    FROM {table_name} t
                    WHERE t.{date_column} >= '{period2_start}' 
                    AND t.{date_column} <= '{period2_end}'
                    AND t.{metric_column} IS NOT NULL
                    {group_by_sql}
                )
                SELECT 
                    {'COALESCE(p1.group_key, p2.group_key) as group_key,' if group_by_column else ''}
                    COALESCE(p1.period1_total, 0) as period1_total,
                    COALESCE(p2.period2_total, 0) as period2_total,
                    COALESCE(p1.period1_avg, 0) as period1_avg,
                    COALESCE(p2.period2_avg, 0) as period2_avg,
                    COALESCE(p1.period1_count, 0) as period1_count,
                    COALESCE(p2.period2_count, 0) as period2_count,
                    COALESCE(p2.period2_total, 0) - COALESCE(p1.period1_total, 0) as total_change,
                    CASE 
                        WHEN COALESCE(p1.period1_total, 0) > 0 
                        THEN ROUND((COALESCE(p2.period2_total, 0) - COALESCE(p1.period1_total, 0)) / p1.period1_total * 100, 2)
                        ELSE NULL 
                    END as percentage_change,
                    COALESCE(p2.period2_avg, 0) - COALESCE(p1.period1_avg, 0) as avg_change
                FROM period1_data p1
                FULL OUTER JOIN period2_data p2 ON {'p1.group_key = p2.group_key' if group_by_column else '1=1'}
                ORDER BY ABS(COALESCE(p2.period2_total, 0) - COALESCE(p1.period1_total, 0)) DESC
            """
            
            results = await conn.fetch(comparison_query)
            
            # Convert results to list of dictionaries
            comparison_data = [dict(row) for row in results]
            
            # Calculate summary statistics
            if comparison_data:
                total_changes = [row['total_change'] for row in comparison_data if row['total_change'] is not None]
                percentage_changes = [row['percentage_change'] for row in comparison_data if row['percentage_change'] is not None]
                
                summary = {
                    "period1_label": f"{period1_start} to {period1_end}",
                    "period2_label": f"{period2_start} to {period2_end}",
                    "total_period1": sum(row['period1_total'] for row in comparison_data),
                    "total_period2": sum(row['period2_total'] for row in comparison_data),
                    "overall_change": sum(total_changes) if total_changes else 0,
                    "average_percentage_change": round(sum(percentage_changes) / len(percentage_changes), 2) if percentage_changes else None,
                    "segments_improved": len([row for row in comparison_data if row['total_change'] and row['total_change'] > 0]),
                    "segments_declined": len([row for row in comparison_data if row['total_change'] and row['total_change'] < 0]),
                    "segments_unchanged": len([row for row in comparison_data if row['total_change'] == 0])
                }
                
                # Calculate overall percentage change
                if summary["total_period1"] > 0:
                    summary["overall_percentage_change"] = round(
                        (summary["total_period2"] - summary["total_period1"]) / summary["total_period1"] * 100, 2
                    )
            else:
                summary = {"message": "No data found for the specified periods"}
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data={
                    "table_name": table_name,
                    "comparison_results": comparison_data,
                    "summary": summary,
                    "parameters": {
                        "date_column": date_column,
                        "metric_column": metric_column,
                        "group_by_column": group_by_column,
                        "period1": f"{period1_start} to {period1_end}",
                        "period2": f"{period2_start} to {period2_end}"
                    }
                },
                metadata={
                    "segments_analyzed": len(comparison_data),
                    "has_improvements": summary.get("segments_improved", 0) > 0,
                    "has_declines": summary.get("segments_declined", 0) > 0
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DetectSeasonalPatternsTool(BaseTool):
    """Detect seasonal patterns in time-series data"""
    
    @property
    def name(self) -> str:
        return "detect_seasonal_patterns"
    
    @property
    def description(self) -> str:
        return "Analyze time-series data to detect seasonal patterns, cyclical trends, and recurring behaviors. Useful for understanding business cycles and forecasting."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table containing time-series data"
            ),
            ToolParameter(
                name="date_column",
                type="string",
                description="Name of the date/timestamp column"
            ),
            ToolParameter(
                name="metric_column",
                type="string",
                description="Name of the metric column to analyze for patterns"
            ),
            ToolParameter(
                name="pattern_type",
                type="string",
                description="Type of seasonal pattern to detect",
                enum_values=["monthly", "quarterly", "weekly", "daily"],
                required=False,
                default="monthly"
            )
        ]
    
    async def execute(self, table_name: str, date_column: str, metric_column: str, pattern_type: str = "monthly") -> ToolResult:
        """Detect seasonal patterns"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Validate columns
            columns_query = """
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = $1
            """
            
            columns = await conn.fetch(columns_query, table_name)
            available_columns = {col['column_name']: col['data_type'] for col in columns}
            
            if date_column not in available_columns:
                return ToolResult(success=False, error=f"Date column '{date_column}' not found")
            
            if metric_column not in available_columns:
                return ToolResult(success=False, error=f"Metric column '{metric_column}' not found")
            
            # Build pattern detection query based on pattern type
            if pattern_type == "monthly":
                time_extract = "EXTRACT(MONTH FROM date_column)"
                time_label = "month_number"
                pattern_query = f"""
                    SELECT 
                        EXTRACT(MONTH FROM {date_column}) as {time_label},
                        TO_CHAR({date_column}, 'Month') as month_name,
                        AVG({metric_column}) as avg_metric,
                        SUM({metric_column}) as total_metric,
                        COUNT(*) as record_count,
                        STDDEV({metric_column}) as std_deviation
                    FROM {table_name}
                    WHERE {date_column} IS NOT NULL AND {metric_column} IS NOT NULL
                    GROUP BY EXTRACT(MONTH FROM {date_column}), TO_CHAR({date_column}, 'Month')
                    ORDER BY EXTRACT(MONTH FROM {date_column})
                """
            
            elif pattern_type == "quarterly":
                pattern_query = f"""
                    SELECT 
                        EXTRACT(QUARTER FROM {date_column}) as quarter_number,
                        'Q' || EXTRACT(QUARTER FROM {date_column}) as quarter_name,
                        AVG({metric_column}) as avg_metric,
                        SUM({metric_column}) as total_metric,
                        COUNT(*) as record_count,
                        STDDEV({metric_column}) as std_deviation
                    FROM {table_name}
                    WHERE {date_column} IS NOT NULL AND {metric_column} IS NOT NULL
                    GROUP BY EXTRACT(QUARTER FROM {date_column})
                    ORDER BY EXTRACT(QUARTER FROM {date_column})
                """
                time_label = "quarter_number"
            
            elif pattern_type == "weekly":
                pattern_query = f"""
                    SELECT 
                        EXTRACT(DOW FROM {date_column}) as day_of_week_number,
                        TO_CHAR({date_column}, 'Day') as day_name,
                        AVG({metric_column}) as avg_metric,
                        SUM({metric_column}) as total_metric,
                        COUNT(*) as record_count,
                        STDDEV({metric_column}) as std_deviation
                    FROM {table_name}
                    WHERE {date_column} IS NOT NULL AND {metric_column} IS NOT NULL
                    GROUP BY EXTRACT(DOW FROM {date_column}), TO_CHAR({date_column}, 'Day')
                    ORDER BY EXTRACT(DOW FROM {date_column})
                """
                time_label = "day_of_week_number"
            
            else:  # daily (hour of day)
                pattern_query = f"""
                    SELECT 
                        EXTRACT(HOUR FROM {date_column}) as hour_of_day,
                        EXTRACT(HOUR FROM {date_column}) || ':00' as hour_label,
                        AVG({metric_column}) as avg_metric,
                        SUM({metric_column}) as total_metric,
                        COUNT(*) as record_count,
                        STDDEV({metric_column}) as std_deviation
                    FROM {table_name}
                    WHERE {date_column} IS NOT NULL AND {metric_column} IS NOT NULL
                    GROUP BY EXTRACT(HOUR FROM {date_column})
                    ORDER BY EXTRACT(HOUR FROM {date_column})
                """
                time_label = "hour_of_day"
            
            pattern_results = await conn.fetch(pattern_query)
            pattern_data = [dict(row) for row in pattern_results]
            
            # Analyze patterns
            if pattern_data:
                avg_metrics = [row['avg_metric'] for row in pattern_data if row['avg_metric'] is not None]
                
                if len(avg_metrics) > 1:
                    overall_avg = sum(avg_metrics) / len(avg_metrics)
                    
                    # Find peaks and troughs
                    peaks = []
                    troughs = []
                    
                    for i, row in enumerate(pattern_data):
                        if row['avg_metric'] is not None:
                            deviation = (row['avg_metric'] - overall_avg) / overall_avg * 100
                            
                            if deviation > 20:  # 20% above average
                                peaks.append({
                                    "period": row.get('month_name') or row.get('quarter_name') or row.get('day_name') or row.get('hour_label'),
                                    "value": row['avg_metric'],
                                    "deviation_percent": round(deviation, 2)
                                })
                            elif deviation < -20:  # 20% below average
                                troughs.append({
                                    "period": row.get('month_name') or row.get('quarter_name') or row.get('day_name') or row.get('hour_label'),
                                    "value": row['avg_metric'],
                                    "deviation_percent": round(deviation, 2)
                                })
                    
                    # Calculate coefficient of variation to measure seasonality strength
                    import statistics
                    cv = statistics.stdev(avg_metrics) / statistics.mean(avg_metrics) * 100 if statistics.mean(avg_metrics) > 0 else 0
                    
                    # Determine seasonality strength
                    if cv > 30:
                        seasonality_strength = "high"
                    elif cv > 15:
                        seasonality_strength = "medium"
                    elif cv > 5:
                        seasonality_strength = "low"
                    else:
                        seasonality_strength = "minimal"
                    
                    analysis = {
                        "pattern_detected": len(peaks) > 0 or len(troughs) > 0,
                        "seasonality_strength": seasonality_strength,
                        "coefficient_of_variation": round(cv, 2),
                        "overall_average": round(overall_avg, 2),
                        "peak_periods": peaks,
                        "trough_periods": troughs,
                        "highest_period": max(pattern_data, key=lambda x: x['avg_metric'] or 0),
                        "lowest_period": min(pattern_data, key=lambda x: x['avg_metric'] or float('inf'))
                    }
                else:
                    analysis = {"message": "Insufficient data for pattern analysis"}
            else:
                analysis = {"message": "No data found for pattern analysis"}
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data={
                    "table_name": table_name,
                    "pattern_type": pattern_type,
                    "pattern_data": pattern_data,
                    "analysis": analysis,
                    "parameters": {
                        "date_column": date_column,
                        "metric_column": metric_column
                    }
                },
                metadata={
                    "periods_analyzed": len(pattern_data),
                    "has_strong_seasonality": analysis.get("seasonality_strength") in ["high", "medium"],
                    "peak_periods_count": len(analysis.get("peak_periods", [])),
                    "trough_periods_count": len(analysis.get("trough_periods", []))
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))
