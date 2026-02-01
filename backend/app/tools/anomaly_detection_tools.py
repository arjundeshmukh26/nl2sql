import json
import statistics
from typing import List, Dict, Any, Optional
from ..database import DatabaseManager
from .base_tool import BaseTool, ToolParameter, ToolResult

class DetectRevenueAnomalies(BaseTool):
    @property
    def name(self) -> str:
        return "detect_revenue_anomalies"

    @property
    def description(self) -> str:
        return "Detects unusual revenue patterns, outliers, and anomalies in any table with a revenue column using statistical analysis. Works with any schema - just provide the table name and revenue column name."

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table to analyze (e.g., 'sales', 'orders')",
                required=True
            ),
            ToolParameter(
                name="revenue_column",
                type="string",
                description="Name of the revenue column (e.g., 'revenue', 'amount', 'total')",
                required=True
            ),
            ToolParameter(
                name="threshold_multiplier",
                type="number",
                description="Standard deviation multiplier for anomaly detection (default: 2.0)",
                required=False
            )
        ]

    async def execute(self, table_name: str, revenue_column: str, threshold_multiplier: float = 2.0) -> ToolResult:
        try:
            # Ensure threshold_multiplier has a valid value
            if threshold_multiplier is None:
                threshold_multiplier = 2.0
            
            # Build dynamic query based on provided table and column names
            query = f"""
                SELECT 
                    *
                FROM {table_name}
                WHERE {revenue_column} IS NOT NULL 
                  AND {revenue_column} > 0
                ORDER BY {revenue_column} DESC 
                LIMIT 1000;
            """
            
            results = await self.db_manager.execute_query(query)
            
            if not results:
                return ToolResult(success=False, error=f"No data found in table '{table_name}'")
            
            # Convert to list of dicts for analysis
            data = [dict(row) for row in results]
            revenues = [float(row[revenue_column]) for row in data if row.get(revenue_column) is not None]
            
            if len(revenues) < 2:
                return ToolResult(success=False, error="Insufficient data for statistical analysis (need at least 2 records)")
            
            # Calculate statistical measures
            mean_revenue = statistics.mean(revenues)
            std_revenue = statistics.stdev(revenues) if len(revenues) > 1 else 0
            median_revenue = statistics.median(revenues)
            
            # Handle edge case where std is 0 (all values are the same)
            if std_revenue == 0:
                std_revenue = mean_revenue * 0.1 if mean_revenue > 0 else 1.0
            
            # Define anomaly thresholds
            upper_threshold = mean_revenue + (threshold_multiplier * std_revenue)
            lower_threshold = max(0, mean_revenue - (threshold_multiplier * std_revenue))
            
            # Find anomalies
            high_anomalies = []
            low_anomalies = []
            
            for row in data:
                value = float(row[revenue_column])
                
                # High value anomalies
                if value > upper_threshold:
                    high_anomalies.append({
                        'record': row,
                        'value': value,
                        'anomaly_type': f'high_{revenue_column}',
                        'deviation_from_mean': value - mean_revenue,
                        'std_deviations': (value - mean_revenue) / std_revenue
                    })
                
                # Low value anomalies (but not zero)
                elif value < lower_threshold and value > 0:
                    low_anomalies.append({
                        'record': row,
                        'value': value,
                        'anomaly_type': f'low_{revenue_column}',
                        'deviation_from_mean': value - mean_revenue,
                        'std_deviations': (value - mean_revenue) / std_revenue
                    })
            
            # Build summary
            summary = {
                'table_analyzed': table_name,
                'column_analyzed': revenue_column,
                'statistical_summary': {
                    'mean': mean_revenue,
                    'median': median_revenue,
                    'std_deviation': std_revenue,
                    'upper_threshold': upper_threshold,
                    'lower_threshold': lower_threshold,
                    'total_records': len(data)
                },
                'anomalies_found': {
                    'high_values': {
                        'count': len(high_anomalies),
                        'records': high_anomalies[:10]  # Limit to top 10
                    },
                    'low_values': {
                        'count': len(low_anomalies),
                        'records': low_anomalies[:10]  # Limit to top 10
                    }
                },
                'total_anomalies': len(high_anomalies) + len(low_anomalies)
            }
            
            return ToolResult(
                success=True,
                data=summary,
                execution_time_ms=800,
                metadata={
                    'analysis_type': 'revenue_anomaly_detection',
                    'threshold_multiplier': threshold_multiplier,
                    'anomalies_percentage': (len(high_anomalies) + len(low_anomalies)) / len(data) * 100
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Error detecting revenue anomalies: {str(e)}")


class DetectTimePatternAnomalies(BaseTool):
    @property
    def name(self) -> str:
        return "detect_time_pattern_anomalies"

    @property
    def description(self) -> str:
        return "Identifies unusual time-based patterns in data, such as gaps in activity, unusual day-of-week patterns, or irregular monthly trends. Works with any table and date column."

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table to analyze (e.g., 'sales')",
                required=True
            ),
            ToolParameter(
                name="date_column",
                type="string",
                description="Name of the date column (e.g., 'sale_date', 'created_at')",
                required=True
            ),
            ToolParameter(
                name="value_column",
                type="string",
                description="Name of the value column to analyze (e.g., 'revenue', 'quantity')",
                required=False
            )
        ]

    async def execute(self, table_name: str, date_column: str, value_column: Optional[str] = None) -> ToolResult:
        try:
            # Use COUNT(*) if no value column specified
            aggregate = f"SUM({value_column})" if value_column else "COUNT(*)"
            agg_label = value_column if value_column else "count"
            
            # Analyze day of week patterns
            dow_query = f"""
                SELECT 
                    EXTRACT(DOW FROM {date_column}::timestamp) as day_of_week,
                    COUNT(*) as transaction_count,
                    {aggregate} as total_{agg_label}
                FROM {table_name}
                WHERE {date_column} IS NOT NULL
                GROUP BY EXTRACT(DOW FROM {date_column}::timestamp)
                ORDER BY day_of_week;
            """
            
            # Analyze monthly patterns
            monthly_query = f"""
                SELECT 
                    DATE_TRUNC('month', {date_column}::timestamp) as month,
                    COUNT(*) as transaction_count,
                    {aggregate} as total_{agg_label}
                FROM {table_name}
                WHERE {date_column} IS NOT NULL
                GROUP BY DATE_TRUNC('month', {date_column}::timestamp)
                ORDER BY month;
            """
            
            # Detect gaps in activity
            gaps_query = f"""
                WITH date_series AS (
                    SELECT generate_series(
                        (SELECT MIN({date_column}::date) FROM {table_name}),
                        (SELECT MAX({date_column}::date) FROM {table_name}),
                        '1 day'::interval
                    )::date as date
                ),
                daily_activity AS (
                    SELECT 
                        {date_column}::date as activity_date,
                        COUNT(*) as activity_count
                    FROM {table_name}
                    GROUP BY {date_column}::date
                )
                SELECT 
                    ds.date,
                    COALESCE(daily_activity.activity_count, 0) as activity_count
                FROM date_series ds
                LEFT JOIN daily_activity ON ds.date = daily_activity.activity_date
                WHERE COALESCE(daily_activity.activity_count, 0) = 0
                ORDER BY ds.date
                LIMIT 50;
            """
            
            dow_results = await self.db_manager.execute_query(dow_query)
            monthly_results = await self.db_manager.execute_query(monthly_query)
            gaps_results = await self.db_manager.execute_query(gaps_query)
            
            # Analyze day of week patterns
            dow_data = [dict(row) for row in dow_results]
            
            anomalies = {
                'table_analyzed': table_name,
                'date_column': date_column,
                'value_column': value_column or 'count',
                'day_of_week_patterns': dow_data,
                'monthly_patterns': [dict(row) for row in monthly_results],
                'activity_gaps': [dict(row) for row in gaps_results]
            }
            
            # Identify unusual day patterns
            if dow_data:
                values = [float(row[f'total_{agg_label}']) for row in dow_data]
                if len(values) > 1:
                    mean_val = statistics.mean(values)
                    std_val = statistics.stdev(values)
                    
                    unusual_days = []
                    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                    for day_data in dow_data:
                        val = float(day_data[f'total_{agg_label}'])
                        if std_val > 0 and abs(val - mean_val) > (1.5 * std_val):
                            unusual_days.append({
                                'day_name': day_names[int(day_data['day_of_week'])],
                                'value': val,
                                'deviation_from_mean': val - mean_val,
                                'is_high': val > mean_val
                            })
                    
                    anomalies['unusual_day_patterns'] = unusual_days
            
            return ToolResult(
                success=True,
                data=anomalies,
                execution_time_ms=800,
                metadata={
                    'analysis_type': 'time_pattern_anomaly_detection',
                    'gaps_found': len(gaps_results),
                    'patterns_analyzed': ['day_of_week', 'monthly', 'gaps']
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Error detecting time pattern anomalies: {str(e)}")


class DetectCustomerBehaviorAnomalies(BaseTool):
    @property
    def name(self) -> str:
        return "detect_customer_behavior_anomalies"

    @property
    def description(self) -> str:
        return "Identifies unusual customer purchasing behaviors and transaction patterns. Works with any schema - requires transaction table and customer identifier column."

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="transaction_table",
                type="string",
                description="Name of the transaction table (e.g., 'sales', 'orders')",
                required=True
            ),
            ToolParameter(
                name="customer_id_column",
                type="string",
                description="Name of the customer ID column (e.g., 'customer_id', 'user_id')",
                required=True
            ),
            ToolParameter(
                name="value_column",
                type="string",
                description="Name of the value column (e.g., 'revenue', 'amount')",
                required=True
            ),
            ToolParameter(
                name="threshold_multiplier",
                type="number",
                description="Standard deviation multiplier for anomaly detection (default: 2.5)",
                required=False
            )
        ]

    async def execute(self, transaction_table: str, customer_id_column: str, value_column: str, threshold_multiplier: float = 2.5) -> ToolResult:
        try:
            # Ensure threshold_multiplier has a valid value
            if threshold_multiplier is None:
                threshold_multiplier = 2.5
            
            # Aggregate customer behavior
            query = f"""
                SELECT
                    {customer_id_column},
                    COUNT(*) as transaction_count,
                    SUM({value_column}) as total_value,
                    AVG({value_column}) as avg_value,
                    MIN({value_column}) as min_value,
                    MAX({value_column}) as max_value
                FROM {transaction_table}
                WHERE {value_column} IS NOT NULL
                GROUP BY {customer_id_column}
                HAVING COUNT(*) > 0
                ORDER BY total_value DESC
                LIMIT 1000;
            """
            
            results = await self.db_manager.execute_query(query)
            
            if not results:
                return ToolResult(success=False, error=f"No customer data found in table '{transaction_table}'")
            
            data = [dict(row) for row in results]
            total_values = [float(row['total_value']) for row in data if row.get('total_value') is not None]
            
            if len(total_values) < 2:
                return ToolResult(success=False, error="Insufficient data for statistical analysis")
            
            # Calculate statistical measures
            mean_value = statistics.mean(total_values)
            std_value = statistics.stdev(total_values) if len(total_values) > 1 else 0
            
            # Handle edge case where std is 0 (all values are the same)
            if std_value == 0:
                std_value = mean_value * 0.1 if mean_value > 0 else 1.0
            
            upper_threshold = mean_value + (threshold_multiplier * std_value)
            lower_threshold = max(0, mean_value - (threshold_multiplier * std_value))
            
            # Find anomalies
            high_value_customers = []
            unusual_frequency = []
            
            for row in data:
                val = float(row['total_value'])
                count = int(row['transaction_count'])
                
                # High value anomalies
                if val > upper_threshold:
                    high_value_customers.append({
                        'customer_id': row[customer_id_column],
                        'total_value': val,
                        'transaction_count': count,
                        'deviation_from_mean': val - mean_value,
                        'std_deviations': (val - mean_value) / std_value
                    })
                
                # Unusual frequency (high count, low value OR low count, high value)
                avg_val_per_transaction = val / count if count > 0 else 0
                if (count > 10 and val < mean_value * 0.5) or (count < 2 and val > mean_value * 1.5):
                    unusual_frequency.append({
                        'customer_id': row[customer_id_column],
                        'total_value': val,
                        'transaction_count': count,
                        'avg_per_transaction': avg_val_per_transaction,
                        'pattern': 'high_frequency_low_value' if count > 10 else 'low_frequency_high_value'
                    })
            
            summary = {
                'table_analyzed': transaction_table,
                'customer_column': customer_id_column,
                'value_column': value_column,
                'statistical_summary': {
                    'mean_customer_value': mean_value,
                    'std_deviation': std_value,
                    'upper_threshold': upper_threshold,
                    'lower_threshold': lower_threshold,
                    'total_customers': len(data)
                },
                'anomalies_found': {
                    'high_value_customers': {
                        'count': len(high_value_customers),
                        'records': high_value_customers[:10]
                    },
                    'unusual_frequency_patterns': {
                        'count': len(unusual_frequency),
                        'records': unusual_frequency[:10]
                    }
                },
                'total_anomalies': len(high_value_customers) + len(unusual_frequency)
            }
            
            return ToolResult(
                success=True,
                data=summary,
                execution_time_ms=800,
                metadata={
                    'analysis_type': 'customer_behavior_anomaly_detection',
                    'threshold_multiplier': threshold_multiplier
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Error detecting customer behavior anomalies: {str(e)}")
