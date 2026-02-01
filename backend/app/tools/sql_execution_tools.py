"""
SQL execution and validation tools - completely general purpose
"""

from typing import List, Dict, Any, Optional
from .base_tool import BaseTool, ToolParameter, ToolResult
import re
import time


class ExecuteSQLQueryTool(BaseTool):
    """Execute SQL queries safely with built-in protections"""
    
    @property
    def name(self) -> str:
        return "execute_sql_query"
    
    @property
    def description(self) -> str:
        return "Execute SQL SELECT queries safely against the database. Automatically applies safety limits and validates query safety. Use this to get data for analysis."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql",
                type="string",
                description="The SQL SELECT query to execute"
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of rows to return",
                required=False,
                default=1000
            ),
            ToolParameter(
                name="explain_plan",
                type="boolean",
                description="Whether to include query execution plan",
                required=False,
                default=False
            )
        ]
    
    async def execute(self, sql: str, limit: int = 1000, explain_plan: bool = False) -> ToolResult:
        """Execute SQL query safely"""
        try:
            # Validate SQL safety
            if not self.db_manager.is_safe_sql(sql):
                return ToolResult(
                    success=False,
                    error="SQL query contains unsafe operations. Only SELECT statements are allowed."
                )
            
            conn = await self.db_manager.get_connection()
            
            # Add safety limits
            safe_sql = self.db_manager.add_safety_limits(sql)
            if limit < 1000:  # Use custom limit if smaller
                safe_sql = re.sub(r'LIMIT \d+', f'LIMIT {limit}', safe_sql, flags=re.IGNORECASE)
                if 'LIMIT' not in safe_sql.upper():
                    safe_sql = safe_sql.rstrip(';') + f' LIMIT {limit};'
            
            start_time = time.time()
            
            # Execute query
            rows = await conn.fetch(safe_sql)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Convert to list of dictionaries
            results = [dict(row) for row in rows]
            
            result_data = {
                "sql_executed": safe_sql,
                "results": results,
                "row_count": len(results),
                "execution_time_ms": execution_time
            }
            
            # Get execution plan if requested
            if explain_plan and results:
                try:
                    explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE) {safe_sql}"
                    plan_result = await conn.fetchval(explain_query)
                    result_data["execution_plan"] = plan_result
                except Exception as e:
                    result_data["execution_plan_error"] = str(e)
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "rows_returned": len(results),
                    "execution_time_ms": execution_time,
                    "query_length": len(safe_sql)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ValidateSQLSyntaxTool(BaseTool):
    """Validate SQL syntax without execution"""
    
    @property
    def name(self) -> str:
        return "validate_sql_syntax"
    
    @property
    def description(self) -> str:
        return "Validate SQL query syntax and safety without executing it. Use this to check queries before execution."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql",
                type="string",
                description="The SQL query to validate"
            )
        ]
    
    async def execute(self, sql: str) -> ToolResult:
        """Validate SQL syntax"""
        try:
            # Basic safety validation
            is_safe = self.db_manager.is_safe_sql(sql)
            
            validation_result = {
                "sql": sql,
                "is_safe": is_safe,
                "validation_errors": [],
                "warnings": [],
                "suggestions": []
            }
            
            if not is_safe:
                validation_result["validation_errors"].append(
                    "Query contains unsafe operations. Only SELECT statements are allowed."
                )
            
            # Basic syntax checks
            sql_upper = sql.strip().upper()
            
            # Check for basic SQL structure
            if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
                validation_result["validation_errors"].append(
                    "Query must start with SELECT or WITH"
                )
            
            # Check for balanced parentheses
            if sql.count('(') != sql.count(')'):
                validation_result["validation_errors"].append(
                    "Unbalanced parentheses in query"
                )
            
            # Check for common issues
            if 'SELECT *' in sql_upper and 'LIMIT' not in sql_upper:
                validation_result["warnings"].append(
                    "SELECT * without LIMIT may return large result sets"
                )
            
            if 'JOIN' in sql_upper and 'ON' not in sql_upper:
                validation_result["warnings"].append(
                    "JOIN without ON clause detected - possible Cartesian product"
                )
            
            # Performance suggestions
            if 'ORDER BY' in sql_upper and 'LIMIT' not in sql_upper:
                validation_result["suggestions"].append(
                    "Consider adding LIMIT when using ORDER BY for better performance"
                )
            
            # Try to validate with database (without execution)
            try:
                conn = await self.db_manager.get_connection()
                
                # Use EXPLAIN to validate syntax
                explain_query = f"EXPLAIN {sql}"
                await conn.fetch(explain_query)
                
                validation_result["syntax_valid"] = True
                
                await conn.close()
                
            except Exception as e:
                validation_result["syntax_valid"] = False
                validation_result["validation_errors"].append(f"Syntax error: {str(e)}")
            
            return ToolResult(
                success=True,
                data=validation_result,
                metadata={
                    "is_valid": len(validation_result["validation_errors"]) == 0,
                    "has_warnings": len(validation_result["warnings"]) > 0,
                    "has_suggestions": len(validation_result["suggestions"]) > 0
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ExplainQueryPlanTool(BaseTool):
    """Get query execution plan and performance analysis"""
    
    @property
    def name(self) -> str:
        return "explain_query_plan"
    
    @property
    def description(self) -> str:
        return "Get detailed execution plan for a SQL query to understand performance characteristics and optimization opportunities."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql",
                type="string",
                description="The SQL query to analyze"
            ),
            ToolParameter(
                name="analyze",
                type="boolean",
                description="Whether to actually execute the query for real timing data",
                required=False,
                default=False
            )
        ]
    
    async def execute(self, sql: str, analyze: bool = False) -> ToolResult:
        """Get query execution plan"""
        try:
            # Validate SQL safety
            if not self.db_manager.is_safe_sql(sql):
                return ToolResult(
                    success=False,
                    error="SQL query contains unsafe operations. Only SELECT statements are allowed."
                )
            
            conn = await self.db_manager.get_connection()
            
            # Build EXPLAIN query
            explain_options = ["FORMAT JSON", "VERBOSE", "BUFFERS"]
            if analyze:
                explain_options.append("ANALYZE")
            
            explain_query = f"EXPLAIN ({', '.join(explain_options)}) {sql}"
            
            # Execute EXPLAIN
            plan_result = await conn.fetchval(explain_query)
            
            # Parse the plan
            plan_data = plan_result[0] if isinstance(plan_result, list) else plan_result
            
            # Extract key metrics
            def extract_plan_metrics(node):
                metrics = {
                    "node_type": node.get("Node Type"),
                    "total_cost": node.get("Total Cost"),
                    "rows": node.get("Plan Rows"),
                    "width": node.get("Plan Width")
                }
                
                if analyze:
                    metrics.update({
                        "actual_time": node.get("Actual Total Time"),
                        "actual_rows": node.get("Actual Rows"),
                        "loops": node.get("Actual Loops")
                    })
                
                return metrics
            
            root_metrics = extract_plan_metrics(plan_data["Plan"])
            
            # Find expensive operations
            expensive_ops = []
            
            def find_expensive_ops(node, threshold_cost=1000):
                if node.get("Total Cost", 0) > threshold_cost:
                    expensive_ops.append({
                        "operation": node.get("Node Type"),
                        "cost": node.get("Total Cost"),
                        "relation": node.get("Relation Name"),
                        "filter": node.get("Filter")
                    })
                
                for child in node.get("Plans", []):
                    find_expensive_ops(child, threshold_cost)
            
            find_expensive_ops(plan_data["Plan"])
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "execution_plan": plan_data,
                    "summary": root_metrics,
                    "expensive_operations": expensive_ops,
                    "analyzed": analyze
                },
                metadata={
                    "total_cost": root_metrics.get("total_cost"),
                    "estimated_rows": root_metrics.get("rows"),
                    "expensive_ops_count": len(expensive_ops)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OptimizeQueryTool(BaseTool):
    """Suggest query optimizations"""
    
    @property
    def name(self) -> str:
        return "optimize_query"
    
    @property
    def description(self) -> str:
        return "Analyze a SQL query and suggest performance optimizations. Provides recommendations for improving query efficiency."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sql",
                type="string",
                description="The SQL query to optimize"
            )
        ]
    
    async def execute(self, sql: str) -> ToolResult:
        """Suggest query optimizations"""
        try:
            suggestions = []
            warnings = []
            
            sql_upper = sql.upper()
            
            # Analyze query patterns
            
            # 1. SELECT * usage
            if 'SELECT *' in sql_upper:
                suggestions.append({
                    "type": "column_selection",
                    "issue": "Using SELECT * returns all columns",
                    "suggestion": "Specify only needed columns to reduce data transfer",
                    "impact": "medium"
                })
            
            # 2. Missing LIMIT
            if 'ORDER BY' in sql_upper and 'LIMIT' not in sql_upper:
                suggestions.append({
                    "type": "result_limiting",
                    "issue": "ORDER BY without LIMIT",
                    "suggestion": "Add LIMIT clause to prevent sorting large result sets",
                    "impact": "high"
                })
            
            # 3. Cartesian products
            join_count = sql_upper.count('JOIN')
            on_count = sql_upper.count(' ON ')
            if join_count > on_count:
                warnings.append({
                    "type": "cartesian_product",
                    "issue": "Possible Cartesian product - JOIN without proper ON clause",
                    "suggestion": "Ensure all JOINs have appropriate ON conditions",
                    "impact": "critical"
                })
            
            # 4. Function usage in WHERE
            if re.search(r'WHERE.*\w+\([^)]*\w+\.[^)]*\)', sql, re.IGNORECASE):
                suggestions.append({
                    "type": "function_in_where",
                    "issue": "Functions in WHERE clause prevent index usage",
                    "suggestion": "Move functions to SELECT or use functional indexes",
                    "impact": "high"
                })
            
            # 5. LIKE patterns
            if re.search(r"LIKE\s+['\"]%", sql, re.IGNORECASE):
                suggestions.append({
                    "type": "like_pattern",
                    "issue": "LIKE patterns starting with % cannot use indexes",
                    "suggestion": "Consider full-text search or restructure query",
                    "impact": "medium"
                })
            
            # 6. Subquery optimization
            if 'IN (' in sql_upper and 'SELECT' in sql_upper:
                suggestions.append({
                    "type": "subquery_optimization",
                    "issue": "IN with subquery can be slow",
                    "suggestion": "Consider using EXISTS or JOIN instead",
                    "impact": "medium"
                })
            
            # 7. DISTINCT usage
            if 'DISTINCT' in sql_upper:
                suggestions.append({
                    "type": "distinct_usage",
                    "issue": "DISTINCT requires sorting/grouping",
                    "suggestion": "Ensure DISTINCT is necessary, consider GROUP BY if aggregating",
                    "impact": "low"
                })
            
            # Get execution plan for more detailed analysis
            try:
                conn = await self.db_manager.get_connection()
                
                if self.db_manager.is_safe_sql(sql):
                    explain_query = f"EXPLAIN (FORMAT JSON) {sql}"
                    plan_result = await conn.fetchval(explain_query)
                    plan_data = plan_result[0] if isinstance(plan_result, list) else plan_result
                    
                    # Analyze plan for specific issues
                    def analyze_plan_node(node):
                        node_type = node.get("Node Type", "")
                        
                        # Sequential scans on large tables
                        if node_type == "Seq Scan":
                            suggestions.append({
                                "type": "sequential_scan",
                                "issue": f"Sequential scan on {node.get('Relation Name', 'table')}",
                                "suggestion": "Consider adding indexes on filtered columns",
                                "impact": "high",
                                "table": node.get("Relation Name")
                            })
                        
                        # Nested loops with high cost
                        if node_type == "Nested Loop" and node.get("Total Cost", 0) > 1000:
                            suggestions.append({
                                "type": "expensive_nested_loop",
                                "issue": "Expensive nested loop join",
                                "suggestion": "Consider hash join or merge join with proper indexes",
                                "impact": "high"
                            })
                        
                        # Sort operations
                        if node_type == "Sort" and node.get("Total Cost", 0) > 500:
                            suggestions.append({
                                "type": "expensive_sort",
                                "issue": "Expensive sort operation",
                                "suggestion": "Consider adding index on sorted columns",
                                "impact": "medium"
                            })
                        
                        # Recursive analysis
                        for child in node.get("Plans", []):
                            analyze_plan_node(child)
                    
                    analyze_plan_node(plan_data["Plan"])
                
                await conn.close()
                
            except Exception as e:
                warnings.append({
                    "type": "analysis_error",
                    "issue": f"Could not analyze execution plan: {str(e)}",
                    "suggestion": "Manual review recommended",
                    "impact": "unknown"
                })
            
            # Prioritize suggestions by impact
            impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            suggestions.sort(key=lambda x: impact_order.get(x["impact"], 4))
            warnings.sort(key=lambda x: impact_order.get(x["impact"], 4))
            
            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "optimization_suggestions": suggestions,
                    "warnings": warnings,
                    "summary": {
                        "total_suggestions": len(suggestions),
                        "critical_issues": len([s for s in suggestions + warnings if s["impact"] == "critical"]),
                        "high_impact": len([s for s in suggestions + warnings if s["impact"] == "high"]),
                        "medium_impact": len([s for s in suggestions + warnings if s["impact"] == "medium"])
                    }
                },
                metadata={
                    "suggestions_count": len(suggestions),
                    "warnings_count": len(warnings),
                    "has_critical_issues": any(s["impact"] == "critical" for s in suggestions + warnings)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))





