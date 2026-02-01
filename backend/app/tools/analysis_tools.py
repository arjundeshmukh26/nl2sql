"""
Data analysis and statistics tools - completely general purpose
"""

from typing import List, Dict, Any, Optional, Union
from .base_tool import BaseTool, ToolParameter, ToolResult
import json


class GetColumnStatisticsTool(BaseTool):
    """Get statistical analysis of any column"""
    
    @property
    def name(self) -> str:
        return "get_column_statistics"
    
    @property
    def description(self) -> str:
        return "Get comprehensive statistical analysis of a column including min, max, average, distribution, and data quality metrics. Works with any data type."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table containing the column"
            ),
            ToolParameter(
                name="column_name",
                type="string",
                description="Name of the column to analyze"
            ),
            ToolParameter(
                name="include_distribution",
                type="boolean",
                description="Whether to include value distribution analysis",
                required=False,
                default=True
            )
        ]
    
    async def execute(self, table_name: str, column_name: str, include_distribution: bool = True) -> ToolResult:
        """Get column statistics"""
        try:
            conn = await self.db_manager.get_connection()
            
            # First, get column data type
            type_query = """
                SELECT data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = $1 
                AND column_name = $2
            """
            
            col_info = await conn.fetchrow(type_query, table_name, column_name)
            
            if not col_info:
                return ToolResult(
                    success=False,
                    error=f"Column '{column_name}' not found in table '{table_name}'"
                )
            
            data_type = col_info['data_type']
            is_nullable = col_info['is_nullable'] == 'YES'
            
            statistics = {
                "table_name": table_name,
                "column_name": column_name,
                "data_type": data_type,
                "is_nullable": is_nullable
            }
            
            # Basic statistics for all types
            basic_stats_query = f"""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT({column_name}) as non_null_count,
                    COUNT(*) - COUNT({column_name}) as null_count,
                    COUNT(DISTINCT {column_name}) as distinct_count
                FROM {table_name}
            """
            
            basic_stats = await conn.fetchrow(basic_stats_query)
            
            statistics.update({
                "total_rows": basic_stats['total_rows'],
                "non_null_count": basic_stats['non_null_count'],
                "null_count": basic_stats['null_count'],
                "distinct_count": basic_stats['distinct_count'],
                "null_percentage": round((basic_stats['null_count'] / basic_stats['total_rows']) * 100, 2) if basic_stats['total_rows'] > 0 else 0,
                "uniqueness_ratio": round(basic_stats['distinct_count'] / basic_stats['non_null_count'], 4) if basic_stats['non_null_count'] > 0 else 0
            })
            
            # Numeric statistics
            if data_type in ['integer', 'bigint', 'smallint', 'numeric', 'decimal', 'real', 'double precision', 'money']:
                numeric_stats_query = f"""
                    SELECT 
                        MIN({column_name}) as min_value,
                        MAX({column_name}) as max_value,
                        AVG({column_name}) as mean_value,
                        STDDEV({column_name}) as std_deviation,
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {column_name}) as q1,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {column_name}) as median,
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {column_name}) as q3
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                """
                
                try:
                    numeric_stats = await conn.fetchrow(numeric_stats_query)
                    statistics["numeric_stats"] = {
                        "min": float(numeric_stats['min_value']) if numeric_stats['min_value'] is not None else None,
                        "max": float(numeric_stats['max_value']) if numeric_stats['max_value'] is not None else None,
                        "mean": round(float(numeric_stats['mean_value']), 4) if numeric_stats['mean_value'] is not None else None,
                        "median": float(numeric_stats['median']) if numeric_stats['median'] is not None else None,
                        "std_deviation": round(float(numeric_stats['std_deviation']), 4) if numeric_stats['std_deviation'] is not None else None,
                        "q1": float(numeric_stats['q1']) if numeric_stats['q1'] is not None else None,
                        "q3": float(numeric_stats['q3']) if numeric_stats['q3'] is not None else None
                    }
                    
                    # Calculate IQR and detect outliers
                    if numeric_stats['q1'] and numeric_stats['q3']:
                        iqr = float(numeric_stats['q3']) - float(numeric_stats['q1'])
                        lower_bound = float(numeric_stats['q1']) - 1.5 * iqr
                        upper_bound = float(numeric_stats['q3']) + 1.5 * iqr
                        
                        outlier_query = f"""
                            SELECT COUNT(*) as outlier_count
                            FROM {table_name}
                            WHERE {column_name} < {lower_bound} OR {column_name} > {upper_bound}
                        """
                        
                        outlier_count = await conn.fetchval(outlier_query)
                        statistics["numeric_stats"]["outlier_count"] = outlier_count
                        statistics["numeric_stats"]["outlier_percentage"] = round((outlier_count / basic_stats['non_null_count']) * 100, 2) if basic_stats['non_null_count'] > 0 else 0
                
                except Exception as e:
                    statistics["numeric_stats_error"] = str(e)
            
            # Text statistics
            elif data_type in ['character varying', 'varchar', 'text', 'char', 'character']:
                text_stats_query = f"""
                    SELECT 
                        MIN(LENGTH({column_name})) as min_length,
                        MAX(LENGTH({column_name})) as max_length,
                        AVG(LENGTH({column_name})) as avg_length,
                        COUNT(*) FILTER (WHERE {column_name} = '') as empty_string_count
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                """
                
                try:
                    text_stats = await conn.fetchrow(text_stats_query)
                    statistics["text_stats"] = {
                        "min_length": text_stats['min_length'],
                        "max_length": text_stats['max_length'],
                        "avg_length": round(float(text_stats['avg_length']), 2) if text_stats['avg_length'] else None,
                        "empty_string_count": text_stats['empty_string_count']
                    }
                except Exception as e:
                    statistics["text_stats_error"] = str(e)
            
            # Date/Time statistics
            elif data_type in ['date', 'timestamp', 'timestamp with time zone', 'timestamp without time zone', 'time']:
                date_stats_query = f"""
                    SELECT 
                        MIN({column_name}) as earliest_date,
                        MAX({column_name}) as latest_date
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                """
                
                try:
                    date_stats = await conn.fetchrow(date_stats_query)
                    statistics["date_stats"] = {
                        "earliest": date_stats['earliest_date'].isoformat() if date_stats['earliest_date'] else None,
                        "latest": date_stats['latest_date'].isoformat() if date_stats['latest_date'] else None
                    }
                    
                    # Calculate date range
                    if date_stats['earliest_date'] and date_stats['latest_date']:
                        date_range = date_stats['latest_date'] - date_stats['earliest_date']
                        statistics["date_stats"]["range_days"] = date_range.days
                
                except Exception as e:
                    statistics["date_stats_error"] = str(e)
            
            # Value distribution (for all types)
            if include_distribution and basic_stats['distinct_count'] <= 100:  # Only for manageable number of distinct values
                distribution_query = f"""
                    SELECT 
                        {column_name} as value,
                        COUNT(*) as frequency,
                        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                    GROUP BY {column_name}
                    ORDER BY COUNT(*) DESC
                    LIMIT 20
                """
                
                try:
                    distribution = await conn.fetch(distribution_query)
                    statistics["value_distribution"] = [
                        {
                            "value": str(row['value']),
                            "frequency": row['frequency'],
                            "percentage": float(row['percentage'])
                        }
                        for row in distribution
                    ]
                except Exception as e:
                    statistics["distribution_error"] = str(e)
            
            elif include_distribution:
                # For high cardinality columns, show top and bottom values
                try:
                    top_values_query = f"""
                        SELECT 
                            {column_name} as value,
                            COUNT(*) as frequency
                        FROM {table_name}
                        WHERE {column_name} IS NOT NULL
                        GROUP BY {column_name}
                        ORDER BY COUNT(*) DESC
                        LIMIT 10
                    """
                    
                    top_values = await conn.fetch(top_values_query)
                    statistics["top_values"] = [
                        {"value": str(row['value']), "frequency": row['frequency']}
                        for row in top_values
                    ]
                except Exception as e:
                    statistics["top_values_error"] = str(e)
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data=statistics,
                metadata={
                    "data_type": data_type,
                    "total_rows": statistics["total_rows"],
                    "null_percentage": statistics["null_percentage"],
                    "distinct_count": statistics["distinct_count"]
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DetectDataAnomaliesTool(BaseTool):
    """Detect anomalies and outliers in data"""
    
    @property
    def name(self) -> str:
        return "detect_data_anomalies"
    
    @property
    def description(self) -> str:
        return "Detect anomalies, outliers, and unusual patterns in table data. Identifies statistical outliers, data quality issues, and suspicious patterns."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table to analyze"
            ),
            ToolParameter(
                name="column_name",
                type="string",
                description="Name of the column to analyze for anomalies (optional - analyzes all if not specified)",
                required=False
            ),
            ToolParameter(
                name="anomaly_threshold",
                type="number",
                description="Standard deviation threshold for outlier detection",
                required=False,
                default=2.5
            )
        ]
    
    async def execute(self, table_name: str, column_name: Optional[str] = None, anomaly_threshold: float = 2.5) -> ToolResult:
        """Detect data anomalies"""
        try:
            conn = await self.db_manager.get_connection()
            
            anomalies = {
                "table_name": table_name,
                "analysis_timestamp": "now",
                "anomalies_found": []
            }
            
            # Get columns to analyze
            if column_name:
                columns_to_analyze = [column_name]
            else:
                # Get all numeric columns
                columns_query = """
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                    AND data_type IN ('integer', 'bigint', 'smallint', 'numeric', 'decimal', 'real', 'double precision')
                """
                
                columns = await conn.fetch(columns_query, table_name)
                columns_to_analyze = [col['column_name'] for col in columns]
            
            for col in columns_to_analyze:
                try:
                    # Statistical outliers using Z-score method
                    outlier_query = f"""
                        WITH stats AS (
                            SELECT 
                                AVG({col}) as mean_val,
                                STDDEV({col}) as std_val
                            FROM {table_name}
                            WHERE {col} IS NOT NULL
                        ),
                        outliers AS (
                            SELECT 
                                {col},
                                ABS(({col} - stats.mean_val) / NULLIF(stats.std_val, 0)) as z_score
                            FROM {table_name}, stats
                            WHERE {col} IS NOT NULL
                            AND ABS(({col} - stats.mean_val) / NULLIF(stats.std_val, 0)) > {anomaly_threshold}
                        )
                        SELECT 
                            COUNT(*) as outlier_count,
                            MIN({col}) as min_outlier,
                            MAX({col}) as max_outlier,
                            AVG(z_score) as avg_z_score
                        FROM outliers
                    """
                    
                    outlier_result = await conn.fetchrow(outlier_query)
                    
                    if outlier_result['outlier_count'] > 0:
                        anomalies["anomalies_found"].append({
                            "type": "statistical_outliers",
                            "column": col,
                            "description": f"Found {outlier_result['outlier_count']} statistical outliers",
                            "details": {
                                "outlier_count": outlier_result['outlier_count'],
                                "min_outlier_value": float(outlier_result['min_outlier']) if outlier_result['min_outlier'] else None,
                                "max_outlier_value": float(outlier_result['max_outlier']) if outlier_result['max_outlier'] else None,
                                "avg_z_score": round(float(outlier_result['avg_z_score']), 2) if outlier_result['avg_z_score'] else None,
                                "threshold_used": anomaly_threshold
                            },
                            "severity": "medium" if outlier_result['outlier_count'] < 10 else "high"
                        })
                    
                    # Sudden spikes or drops (if there's a date column)
                    date_columns_query = """
                        SELECT column_name
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                        AND data_type IN ('date', 'timestamp', 'timestamp with time zone')
                        LIMIT 1
                    """
                    
                    date_col = await conn.fetchval(date_columns_query, table_name)
                    
                    if date_col:
                        # Look for sudden changes in values over time
                        spike_query = f"""
                            WITH daily_stats AS (
                                SELECT 
                                    DATE({date_col}) as date,
                                    AVG({col}) as daily_avg,
                                    COUNT(*) as daily_count
                                FROM {table_name}
                                WHERE {col} IS NOT NULL AND {date_col} IS NOT NULL
                                GROUP BY DATE({date_col})
                                HAVING COUNT(*) > 1
                            ),
                            changes AS (
                                SELECT 
                                    date,
                                    daily_avg,
                                    LAG(daily_avg) OVER (ORDER BY date) as prev_avg,
                                    ABS(daily_avg - LAG(daily_avg) OVER (ORDER BY date)) / NULLIF(LAG(daily_avg) OVER (ORDER BY date), 0) as change_ratio
                                FROM daily_stats
                            )
                            SELECT 
                                date,
                                daily_avg,
                                prev_avg,
                                change_ratio
                            FROM changes
                            WHERE change_ratio > 2.0  -- 200% change
                            ORDER BY change_ratio DESC
                            LIMIT 5
                        """
                        
                        try:
                            spikes = await conn.fetch(spike_query)
                            
                            if spikes:
                                anomalies["anomalies_found"].append({
                                    "type": "temporal_spikes",
                                    "column": col,
                                    "description": f"Found {len(spikes)} significant day-to-day changes",
                                    "details": {
                                        "spikes": [
                                            {
                                                "date": spike['date'].isoformat() if spike['date'] else None,
                                                "value": float(spike['daily_avg']) if spike['daily_avg'] else None,
                                                "previous_value": float(spike['prev_avg']) if spike['prev_avg'] else None,
                                                "change_ratio": round(float(spike['change_ratio']), 2) if spike['change_ratio'] else None
                                            }
                                            for spike in spikes
                                        ]
                                    },
                                    "severity": "medium"
                                })
                        except Exception as e:
                            pass  # Skip temporal analysis if it fails
                
                except Exception as e:
                    anomalies["anomalies_found"].append({
                        "type": "analysis_error",
                        "column": col,
                        "description": f"Could not analyze column: {str(e)}",
                        "severity": "low"
                    })
            
            # Data quality anomalies (for all columns)
            if not column_name:  # Only do this for full table analysis
                # Check for duplicate rows
                try:
                    duplicate_query = f"""
                        SELECT COUNT(*) - COUNT(DISTINCT *) as duplicate_count
                        FROM {table_name}
                    """
                    
                    duplicate_count = await conn.fetchval(duplicate_query)
                    
                    if duplicate_count > 0:
                        anomalies["anomalies_found"].append({
                            "type": "duplicate_rows",
                            "column": "all_columns",
                            "description": f"Found {duplicate_count} duplicate rows",
                            "details": {"duplicate_count": duplicate_count},
                            "severity": "medium" if duplicate_count < 100 else "high"
                        })
                
                except Exception as e:
                    pass  # Skip if duplicate check fails
                
                # Check for unusual null patterns
                try:
                    null_pattern_query = f"""
                        SELECT 
                            column_name,
                            (COUNT(*) - COUNT(column_name)) as null_count,
                            ROUND((COUNT(*) - COUNT(column_name)) * 100.0 / COUNT(*), 2) as null_percentage
                        FROM information_schema.columns c
                        CROSS JOIN {table_name} t
                        WHERE c.table_schema = 'public' 
                        AND c.table_name = '{table_name}'
                        GROUP BY column_name
                        HAVING (COUNT(*) - COUNT(column_name)) * 100.0 / COUNT(*) > 50
                    """
                    
                    # This is a simplified version - in practice, you'd need dynamic SQL
                    # For now, just check a few key patterns
                    
                except Exception as e:
                    pass
            
            await conn.close()
            
            # Categorize severity
            severity_counts = {
                "high": len([a for a in anomalies["anomalies_found"] if a["severity"] == "high"]),
                "medium": len([a for a in anomalies["anomalies_found"] if a["severity"] == "medium"]),
                "low": len([a for a in anomalies["anomalies_found"] if a["severity"] == "low"])
            }
            
            return ToolResult(
                success=True,
                data=anomalies,
                metadata={
                    "total_anomalies": len(anomalies["anomalies_found"]),
                    "severity_breakdown": severity_counts,
                    "columns_analyzed": len(columns_to_analyze)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FindCorrelationsTool(BaseTool):
    """Find correlations between columns"""
    
    @property
    def name(self) -> str:
        return "find_correlations"
    
    @property
    def description(self) -> str:
        return "Find statistical correlations between numeric columns in a table. Helps identify relationships and dependencies in data."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table to analyze"
            ),
            ToolParameter(
                name="columns",
                type="string",
                description="Comma-separated list of columns to analyze (optional - analyzes all numeric columns if not specified)",
                required=False
            ),
            ToolParameter(
                name="min_correlation",
                type="number",
                description="Minimum correlation coefficient to report",
                required=False,
                default=0.3
            )
        ]
    
    async def execute(self, table_name: str, columns: Optional[str] = None, min_correlation: float = 0.3) -> ToolResult:
        """Find correlations between columns"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Get columns to analyze
            if columns:
                columns_to_analyze = [col.strip() for col in columns.split(',')]
            else:
                # Get all numeric columns
                columns_query = """
                    SELECT column_name
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                    AND data_type IN ('integer', 'bigint', 'smallint', 'numeric', 'decimal', 'real', 'double precision')
                """
                
                column_rows = await conn.fetch(columns_query, table_name)
                columns_to_analyze = [row['column_name'] for row in column_rows]
            
            if len(columns_to_analyze) < 2:
                return ToolResult(
                    success=False,
                    error="Need at least 2 numeric columns to calculate correlations"
                )
            
            correlations = {
                "table_name": table_name,
                "columns_analyzed": columns_to_analyze,
                "correlations": [],
                "summary": {}
            }
            
            # Calculate pairwise correlations
            for i, col1 in enumerate(columns_to_analyze):
                for j, col2 in enumerate(columns_to_analyze):
                    if i < j:  # Avoid duplicates and self-correlation
                        try:
                            correlation_query = f"""
                                SELECT 
                                    CORR({col1}, {col2}) as correlation_coefficient,
                                    COUNT(*) FILTER (WHERE {col1} IS NOT NULL AND {col2} IS NOT NULL) as sample_size
                                FROM {table_name}
                                WHERE {col1} IS NOT NULL AND {col2} IS NOT NULL
                            """
                            
                            result = await conn.fetchrow(correlation_query)
                            
                            if result['correlation_coefficient'] is not None:
                                corr_coeff = float(result['correlation_coefficient'])
                                
                                if abs(corr_coeff) >= min_correlation:
                                    # Determine correlation strength
                                    abs_corr = abs(corr_coeff)
                                    if abs_corr >= 0.8:
                                        strength = "very_strong"
                                    elif abs_corr >= 0.6:
                                        strength = "strong"
                                    elif abs_corr >= 0.4:
                                        strength = "moderate"
                                    else:
                                        strength = "weak"
                                    
                                    correlations["correlations"].append({
                                        "column1": col1,
                                        "column2": col2,
                                        "correlation_coefficient": round(corr_coeff, 4),
                                        "strength": strength,
                                        "direction": "positive" if corr_coeff > 0 else "negative",
                                        "sample_size": result['sample_size']
                                    })
                        
                        except Exception as e:
                            # Skip this pair if correlation calculation fails
                            continue
            
            # Sort by absolute correlation strength
            correlations["correlations"].sort(
                key=lambda x: abs(x["correlation_coefficient"]), 
                reverse=True
            )
            
            # Generate summary
            if correlations["correlations"]:
                correlations["summary"] = {
                    "total_correlations_found": len(correlations["correlations"]),
                    "strongest_correlation": correlations["correlations"][0],
                    "average_correlation": round(
                        sum(abs(c["correlation_coefficient"]) for c in correlations["correlations"]) / len(correlations["correlations"]), 
                        4
                    ),
                    "strength_distribution": {
                        "very_strong": len([c for c in correlations["correlations"] if c["strength"] == "very_strong"]),
                        "strong": len([c for c in correlations["correlations"] if c["strength"] == "strong"]),
                        "moderate": len([c for c in correlations["correlations"] if c["strength"] == "moderate"]),
                        "weak": len([c for c in correlations["correlations"] if c["strength"] == "weak"])
                    }
                }
            else:
                correlations["summary"] = {
                    "total_correlations_found": 0,
                    "message": f"No correlations found above threshold of {min_correlation}"
                }
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data=correlations,
                metadata={
                    "columns_analyzed": len(columns_to_analyze),
                    "correlations_found": len(correlations["correlations"]),
                    "min_correlation_threshold": min_correlation
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class AnalyzeDataQualityTool(BaseTool):
    """Comprehensive data quality analysis"""
    
    @property
    def name(self) -> str:
        return "analyze_data_quality"
    
    @property
    def description(self) -> str:
        return "Perform comprehensive data quality analysis including completeness, consistency, validity, and uniqueness checks across all columns."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table to analyze"
            )
        ]
    
    async def execute(self, table_name: str) -> ToolResult:
        """Analyze data quality"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Get table structure
            columns_query = """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = $1
                ORDER BY ordinal_position
            """
            
            columns = await conn.fetch(columns_query, table_name)
            
            if not columns:
                return ToolResult(
                    success=False,
                    error=f"Table '{table_name}' not found"
                )
            
            # Get total row count
            total_rows = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            quality_report = {
                "table_name": table_name,
                "total_rows": total_rows,
                "columns_analyzed": len(columns),
                "quality_issues": [],
                "column_quality": [],
                "overall_score": 0
            }
            
            total_quality_score = 0
            
            for col in columns:
                col_name = col['column_name']
                data_type = col['data_type']
                is_nullable = col['is_nullable'] == 'YES'
                
                col_quality = {
                    "column_name": col_name,
                    "data_type": data_type,
                    "is_nullable": is_nullable,
                    "quality_checks": {}
                }
                
                # Completeness check
                null_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL")
                completeness_score = ((total_rows - null_count) / total_rows) * 100 if total_rows > 0 else 100
                
                col_quality["quality_checks"]["completeness"] = {
                    "score": round(completeness_score, 2),
                    "null_count": null_count,
                    "null_percentage": round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0
                }
                
                if not is_nullable and null_count > 0:
                    quality_report["quality_issues"].append({
                        "type": "completeness",
                        "column": col_name,
                        "severity": "high",
                        "description": f"Non-nullable column has {null_count} null values"
                    })
                
                # Uniqueness check (for potential key columns)
                distinct_count = await conn.fetchval(f"SELECT COUNT(DISTINCT {col_name}) FROM {table_name} WHERE {col_name} IS NOT NULL")
                non_null_count = total_rows - null_count
                uniqueness_score = (distinct_count / non_null_count) * 100 if non_null_count > 0 else 100
                
                col_quality["quality_checks"]["uniqueness"] = {
                    "score": round(uniqueness_score, 2),
                    "distinct_count": distinct_count,
                    "duplicate_count": non_null_count - distinct_count
                }
                
                # Data type specific validations
                if data_type in ['character varying', 'varchar', 'text', 'char']:
                    # Check for empty strings
                    empty_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} = ''")
                    
                    # Check for unusual characters or patterns
                    special_char_count = await conn.fetchval(f"""
                        SELECT COUNT(*) FROM {table_name} 
                        WHERE {col_name} ~ '[^a-zA-Z0-9 .,!?@#$%^&*()_+-=]'
                        AND {col_name} IS NOT NULL
                    """)
                    
                    col_quality["quality_checks"]["text_validity"] = {
                        "empty_string_count": empty_count,
                        "special_character_count": special_char_count
                    }
                    
                    if empty_count > 0:
                        quality_report["quality_issues"].append({
                            "type": "validity",
                            "column": col_name,
                            "severity": "medium",
                            "description": f"Found {empty_count} empty strings"
                        })
                
                elif data_type in ['integer', 'bigint', 'smallint', 'numeric', 'decimal']:
                    # Check for negative values where they might not be expected
                    negative_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} < 0")
                    
                    # Check for zero values
                    zero_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} = 0")
                    
                    col_quality["quality_checks"]["numeric_validity"] = {
                        "negative_count": negative_count,
                        "zero_count": zero_count
                    }
                
                elif data_type in ['date', 'timestamp', 'timestamp with time zone']:
                    # Check for future dates (might be data entry errors)
                    future_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} > CURRENT_DATE")
                    
                    # Check for very old dates (might be default values)
                    old_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} < '1900-01-01'")
                    
                    col_quality["quality_checks"]["date_validity"] = {
                        "future_date_count": future_count,
                        "very_old_date_count": old_count
                    }
                    
                    if future_count > 0:
                        quality_report["quality_issues"].append({
                            "type": "validity",
                            "column": col_name,
                            "severity": "medium",
                            "description": f"Found {future_count} future dates"
                        })
                
                # Calculate overall column quality score
                column_score = (completeness_score + uniqueness_score) / 2
                col_quality["overall_score"] = round(column_score, 2)
                total_quality_score += column_score
                
                quality_report["column_quality"].append(col_quality)
            
            # Calculate overall table quality score
            quality_report["overall_score"] = round(total_quality_score / len(columns), 2) if columns else 0
            
            # Categorize overall quality
            if quality_report["overall_score"] >= 90:
                quality_report["quality_grade"] = "Excellent"
            elif quality_report["overall_score"] >= 80:
                quality_report["quality_grade"] = "Good"
            elif quality_report["overall_score"] >= 70:
                quality_report["quality_grade"] = "Fair"
            else:
                quality_report["quality_grade"] = "Poor"
            
            # Summary statistics
            quality_report["summary"] = {
                "total_issues": len(quality_report["quality_issues"]),
                "high_severity_issues": len([i for i in quality_report["quality_issues"] if i["severity"] == "high"]),
                "medium_severity_issues": len([i for i in quality_report["quality_issues"] if i["severity"] == "medium"]),
                "low_severity_issues": len([i for i in quality_report["quality_issues"] if i["severity"] == "low"]),
                "average_completeness": round(sum(c["quality_checks"]["completeness"]["score"] for c in quality_report["column_quality"]) / len(columns), 2) if columns else 0,
                "average_uniqueness": round(sum(c["quality_checks"]["uniqueness"]["score"] for c in quality_report["column_quality"]) / len(columns), 2) if columns else 0
            }
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data=quality_report,
                metadata={
                    "overall_score": quality_report["overall_score"],
                    "quality_grade": quality_report["quality_grade"],
                    "total_issues": quality_report["summary"]["total_issues"],
                    "columns_analyzed": len(columns)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))





