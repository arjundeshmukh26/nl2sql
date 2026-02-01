"""
Database discovery and schema tools - completely general purpose
"""

from typing import List, Dict, Any, Optional
from .base_tool import BaseTool, ToolParameter, ToolResult
import asyncpg


class GetDatabaseSchemaTool(BaseTool):
    """Get complete database schema information"""
    
    @property
    def name(self) -> str:
        return "get_database_schema"
    
    @property
    def description(self) -> str:
        return "Get comprehensive database schema including all tables, columns, data types, and relationships. Essential for understanding any database structure."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="include_system_tables",
                type="boolean",
                description="Whether to include system/internal tables",
                required=False,
                default=False
            )
        ]
    
    async def execute(self, include_system_tables: bool = False) -> ToolResult:
        """Get database schema"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Get all tables
            table_query = """
                SELECT 
                    schemaname,
                    tablename,
                    tableowner
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """
            
            if include_system_tables:
                table_query = table_query.replace("WHERE schemaname = 'public'", "")
            
            tables = await conn.fetch(table_query)
            
            schema_info = {
                "tables": [],
                "relationships": [],
                "total_tables": len(tables)
            }
            
            # Get detailed info for each table
            for table in tables:
                table_name = table['tablename']
                schema_name = table['schemaname']
                
                # Get columns
                columns_query = """
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns 
                    WHERE table_schema = $1 AND table_name = $2
                    ORDER BY ordinal_position
                """
                
                columns = await conn.fetch(columns_query, schema_name, table_name)
                
                # Get primary keys
                pk_query = """
                    SELECT column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_schema = $1 
                        AND tc.table_name = $2 
                        AND tc.constraint_type = 'PRIMARY KEY'
                """
                
                primary_keys = await conn.fetch(pk_query, schema_name, table_name)
                
                # Get foreign keys
                fk_query = """
                    SELECT 
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY' 
                        AND tc.table_schema = $1
                        AND tc.table_name = $2
                """
                
                foreign_keys = await conn.fetch(fk_query, schema_name, table_name)
                
                # Get row count estimate
                count_query = f"""
                    SELECT reltuples::BIGINT AS estimate 
                    FROM pg_class 
                    WHERE relname = $1
                """
                
                try:
                    row_count = await conn.fetchval(count_query, table_name)
                except:
                    row_count = None
                
                table_info = {
                    "table_name": table_name,
                    "schema_name": schema_name,
                    "columns": [
                        {
                            "name": col['column_name'],
                            "type": col['data_type'],
                            "nullable": col['is_nullable'] == 'YES',
                            "default": col['column_default'],
                            "max_length": col['character_maximum_length'],
                            "precision": col['numeric_precision'],
                            "scale": col['numeric_scale']
                        }
                        for col in columns
                    ],
                    "primary_keys": [pk['column_name'] for pk in primary_keys],
                    "foreign_keys": [
                        {
                            "column": fk['column_name'],
                            "references_table": fk['foreign_table_name'],
                            "references_column": fk['foreign_column_name']
                        }
                        for fk in foreign_keys
                    ],
                    "estimated_rows": row_count
                }
                
                schema_info["tables"].append(table_info)
                
                # Add relationships to global list
                for fk in foreign_keys:
                    schema_info["relationships"].append({
                        "from_table": table_name,
                        "from_column": fk['column_name'],
                        "to_table": fk['foreign_table_name'],
                        "to_column": fk['foreign_column_name']
                    })
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data=schema_info,
                metadata={
                    "total_tables": len(schema_info["tables"]),
                    "total_relationships": len(schema_info["relationships"])
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DescribeTableTool(BaseTool):
    """Get detailed information about a specific table"""
    
    @property
    def name(self) -> str:
        return "describe_table"
    
    @property
    def description(self) -> str:
        return "Get detailed information about a specific table including columns, constraints, indexes, and sample data. Use this to understand table structure and content."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table to describe"
            ),
            ToolParameter(
                name="include_sample_data",
                type="boolean",
                description="Whether to include sample rows from the table",
                required=False,
                default=True
            ),
            ToolParameter(
                name="sample_size",
                type="integer",
                description="Number of sample rows to return",
                required=False,
                default=5
            )
        ]
    
    async def execute(self, table_name: str, include_sample_data: bool = True, sample_size: int = 5) -> ToolResult:
        """Describe table in detail"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Check if table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
            """, table_name)
            
            if not table_exists:
                return ToolResult(
                    success=False,
                    error=f"Table '{table_name}' does not exist"
                )
            
            # Get column information
            columns_query = """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    ordinal_position
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position
            """
            
            columns = await conn.fetch(columns_query, table_name)
            
            # Get constraints
            constraints_query = """
                SELECT 
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                LEFT JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_schema = 'public' AND tc.table_name = $1
            """
            
            constraints = await conn.fetch(constraints_query, table_name)
            
            # Get indexes
            indexes_query = """
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE schemaname = 'public' AND tablename = $1
            """
            
            indexes = await conn.fetch(indexes_query, table_name)
            
            # Get table statistics
            stats_query = f"""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    most_common_vals,
                    most_common_freqs,
                    histogram_bounds
                FROM pg_stats 
                WHERE schemaname = 'public' AND tablename = $1
            """
            
            stats = await conn.fetch(stats_query, table_name)
            
            # Get row count
            try:
                row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            except:
                row_count = None
            
            table_info = {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col['column_name'],
                        "type": col['data_type'],
                        "nullable": col['is_nullable'] == 'YES',
                        "default": col['column_default'],
                        "max_length": col['character_maximum_length'],
                        "precision": col['numeric_precision'],
                        "scale": col['numeric_scale'],
                        "position": col['ordinal_position']
                    }
                    for col in columns
                ],
                "constraints": [
                    {
                        "name": c['constraint_name'],
                        "type": c['constraint_type'],
                        "column": c['column_name'],
                        "references_table": c['foreign_table_name'],
                        "references_column": c['foreign_column_name']
                    }
                    for c in constraints
                ],
                "indexes": [
                    {
                        "name": idx['indexname'],
                        "definition": idx['indexdef']
                    }
                    for idx in indexes
                ],
                "statistics": [
                    {
                        "column": stat['attname'],
                        "distinct_values": stat['n_distinct'],
                        "common_values": stat['most_common_vals'],
                        "common_frequencies": stat['most_common_freqs']
                    }
                    for stat in stats
                ],
                "row_count": row_count
            }
            
            # Get sample data if requested
            if include_sample_data and row_count and row_count > 0:
                try:
                    sample_query = f"SELECT * FROM {table_name} LIMIT $1"
                    sample_rows = await conn.fetch(sample_query, sample_size)
                    
                    table_info["sample_data"] = [
                        dict(row) for row in sample_rows
                    ]
                except Exception as e:
                    table_info["sample_data_error"] = str(e)
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data=table_info,
                metadata={
                    "column_count": len(columns),
                    "constraint_count": len(constraints),
                    "index_count": len(indexes),
                    "row_count": row_count
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetTableSampleDataTool(BaseTool):
    """Get sample data from any table"""
    
    @property
    def name(self) -> str:
        return "get_table_sample_data"
    
    @property
    def description(self) -> str:
        return "Get sample rows from a table to understand the actual data content and patterns. Useful for data exploration and understanding value formats."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Name of the table to sample"
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Number of sample rows to return",
                required=False,
                default=10
            ),
            ToolParameter(
                name="columns",
                type="string",
                description="Comma-separated list of specific columns to include (optional)",
                required=False
            ),
            ToolParameter(
                name="where_clause",
                type="string",
                description="Optional WHERE clause to filter sample data",
                required=False
            )
        ]
    
    async def execute(self, table_name: str, limit: int = 10, columns: Optional[str] = None, where_clause: Optional[str] = None) -> ToolResult:
        """Get sample data from table"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Validate table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
            """, table_name)
            
            if not table_exists:
                return ToolResult(
                    success=False,
                    error=f"Table '{table_name}' does not exist"
                )
            
            # Build query
            select_columns = columns if columns else "*"
            query = f"SELECT {select_columns} FROM {table_name}"
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            query += f" LIMIT {limit}"
            
            # Execute query
            rows = await conn.fetch(query)
            
            # Convert to list of dictionaries
            sample_data = [dict(row) for row in rows]
            
            # Get column info for metadata
            if columns:
                selected_columns = [col.strip() for col in columns.split(',')]
            else:
                col_query = """
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = $1
                    ORDER BY ordinal_position
                """
                col_info = await conn.fetch(col_query, table_name)
                selected_columns = [col['column_name'] for col in col_info]
            
            await conn.close()
            
            return ToolResult(
                success=True,
                data={
                    "table_name": table_name,
                    "sample_data": sample_data,
                    "columns": selected_columns,
                    "row_count": len(sample_data)
                },
                metadata={
                    "query_executed": query,
                    "rows_returned": len(sample_data),
                    "columns_selected": len(selected_columns)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class EstimateTableSizeTool(BaseTool):
    """Get table size and row count estimates"""
    
    @property
    def name(self) -> str:
        return "estimate_table_size"
    
    @property
    def description(self) -> str:
        return "Get table size estimates including row count, disk usage, and performance characteristics. Useful for understanding data volume and query planning."
    
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
        """Get table size estimates"""
        try:
            conn = await self.db_manager.get_connection()
            
            # Get table size information
            size_query = """
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    most_common_vals,
                    avg_width,
                    n_distinct,
                    null_frac
                FROM pg_stats 
                WHERE schemaname = 'public' AND tablename = $1
            """
            
            stats = await conn.fetch(size_query, table_name)
            
            # Get physical size
            physical_size_query = """
                SELECT 
                    pg_size_pretty(pg_total_relation_size($1)) as total_size,
                    pg_size_pretty(pg_relation_size($1)) as table_size,
                    pg_size_pretty(pg_indexes_size($1)) as indexes_size
            """
            
            try:
                size_info = await conn.fetchrow(physical_size_query, table_name)
            except:
                size_info = None
            
            # Get row count estimate
            row_estimate_query = """
                SELECT reltuples::BIGINT AS estimated_rows
                FROM pg_class 
                WHERE relname = $1
            """
            
            estimated_rows = await conn.fetchval(row_estimate_query, table_name)
            
            # Get exact count for smaller tables
            exact_count = None
            if estimated_rows and estimated_rows < 100000:  # Only for smaller tables
                try:
                    exact_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                except:
                    pass
            
            await conn.close()
            
            result_data = {
                "table_name": table_name,
                "estimated_rows": estimated_rows,
                "exact_rows": exact_count,
                "column_statistics": [
                    {
                        "column": stat['attname'],
                        "distinct_values": stat['n_distinct'],
                        "average_width": stat['avg_width'],
                        "null_fraction": stat['null_frac']
                    }
                    for stat in stats
                ] if stats else []
            }
            
            if size_info:
                result_data.update({
                    "total_size": size_info['total_size'],
                    "table_size": size_info['table_size'],
                    "indexes_size": size_info['indexes_size']
                })
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "has_exact_count": exact_count is not None,
                    "column_count": len(stats) if stats else 0
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))





