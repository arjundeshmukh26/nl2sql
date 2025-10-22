import asyncpg
import re
from typing import List, Dict, Any, Optional
from .config import settings


class DatabaseManager:
    def __init__(self):
        self.connection_string = settings.database_url
        self.max_results = settings.max_query_results
    
    async def get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(self.connection_string)
    
    def is_safe_sql(self, sql: str) -> bool:
        """Validate that SQL is safe (SELECT-only, no dangerous operations)"""
        # Remove comments and normalize whitespace
        cleaned_sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        cleaned_sql = re.sub(r'/\*.*?\*/', '', cleaned_sql, flags=re.DOTALL)
        cleaned_sql = cleaned_sql.strip().upper()
        
        # Must start with SELECT
        if not cleaned_sql.startswith('SELECT'):
            return False
        
        # Dangerous keywords that should not appear
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
            'TRUNCATE', 'REPLACE', 'MERGE', 'EXEC', 'EXECUTE',
            'CALL', 'DECLARE', 'SET', 'GRANT', 'REVOKE'
        ]
        
        for keyword in dangerous_keywords:
            if re.search(r'\b' + keyword + r'\b', cleaned_sql):
                return False
        
        return True
    
    def add_safety_limits(self, sql: str) -> str:
        """Add LIMIT clause if not present"""
        if 'LIMIT' not in sql.upper():
            # Add limit before any ORDER BY clause or at the end
            if 'ORDER BY' in sql.upper():
                sql = re.sub(
                    r'(ORDER BY.*?)(?=;|$)', 
                    rf'\1 LIMIT {self.max_results}', 
                    sql, 
                    flags=re.IGNORECASE
                )
            else:
                sql = sql.rstrip(';') + f' LIMIT {self.max_results};'
        
        return sql
    
    async def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query safely and return results"""
        
        # Validate SQL safety
        if not self.is_safe_sql(sql):
            raise ValueError("SQL query contains unsafe operations. Only SELECT statements are allowed.")
        
        # Add safety limits
        safe_sql = self.add_safety_limits(sql)
        
        conn = None
        try:
            # Get connection
            conn = await self.get_connection()
            
            # Execute query
            rows = await conn.fetch(safe_sql)
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                row_dict = {}
                for key, value in row.items():
                    # Handle different data types
                    if value is None:
                        row_dict[key] = None
                    elif hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[key] = value.isoformat()
                    else:
                        row_dict[key] = value
                results.append(row_dict)
            
            return results
                
        except Exception as e:
            # Re-raise with more context
            raise Exception(f"SQL execution failed: {str(e)}")
        
        finally:
            if conn:
                await conn.close()
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        conn = None
        try:
            conn = await self.get_connection()
            await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False
        finally:
            if conn:
                await conn.close()