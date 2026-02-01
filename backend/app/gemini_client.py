import json
import logging
import google.generativeai as genai
from typing import Dict, Any
from .config import settings
from .models import SQLResponse

# Configure logging
logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.gemini_api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generation config for consistent JSON output
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048,
        )
    
    async def nl_to_sql(self, user_query: str, schema: str) -> SQLResponse:
        """Convert natural language to SQL using Gemini 2.5 Pro"""
        
        logger.info(f"🔄 Converting NL to SQL: '{user_query}'")
        
        prompt = self._build_prompt(user_query, schema)
        
        try:
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Extract and parse JSON response
            content = response.text.strip()
            logger.info(f"📝 Raw LLM Response: {content}")
            
            # Try to extract JSON from the response
            try:
                # Remove any markdown formatting
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                result = json.loads(content)
                logger.info(f"✅ Parsed JSON: {result}")
                
                sql_response = SQLResponse(
                    sql=result.get("sql", ""),
                    explanation=result.get("explanation", "")
                )
                
                logger.info(f"🔍 Generated SQL: {sql_response.sql}")
                if sql_response.explanation:
                    logger.info(f"💡 Explanation: {sql_response.explanation}")
                
                return sql_response
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parsing failed: {e}")
                logger.info(f"📄 Attempting fallback SQL extraction from: {content}")
                # Fallback: try to extract SQL from response
                sql = self._extract_sql_fallback(content)
                logger.info(f"🔧 Fallback SQL: {sql}")
                return SQLResponse(
                    sql=sql,
                    explanation="Generated SQL (JSON parsing failed)"
                )
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Gemini API call failed: {error_msg}")
            
            # Handle rate limiting specifically
            if "429" in error_msg or "quota" in error_msg.lower() or "Resource exhausted" in error_msg:
                logger.warning(f"⚠️ Rate limit exceeded: {error_msg}")
                raise Exception(f"API quota exceeded. Please wait 32 seconds before trying again. Details: {error_msg}")
            
            raise Exception(f"Gemini API call failed: {error_msg}")
    
    def _build_prompt(self, user_query: str, schema: str) -> str:
        """Build the complete prompt for NL2SQL conversion"""
        
        return f"""You are an expert data analyst and SQL developer.
Your job is to convert a user's natural language query into a valid PostgreSQL SQL query 
that retrieves the correct information from the database, based on the given schema.

### Rules:
1. Output must be **valid PostgreSQL SQL**.
2. Only generate **SELECT** queries (no INSERT, UPDATE, DELETE, DROP).
3. If aggregation is needed (e.g., total, average, count), use appropriate GROUP BY clauses.
4. Always use **table aliases** for clarity.
5. Use **JOINs** correctly based on foreign key relationships.
6. Prefer **explicit JOIN syntax** over implicit joins.
7. Include **ORDER BY** or **LIMIT** when relevant.
8. Use proper date filtering if the query mentions time (e.g., "this year", "last month").
9. Return only the SQL query, without markdown formatting or explanations unless specifically asked.
10. Do not make up tables or columns not present in the schema.

---

### Database Schema

{schema}

---

### User Query
"{user_query}"

---

### Expected Output Format
Return JSON in this format:
{{
  "sql": "SELECT ...;",
  "explanation": "Brief natural language reasoning (optional)"
}}"""
    
    def _extract_sql_fallback(self, content: str) -> str:
        """Extract SQL from response when JSON parsing fails"""
        lines = content.split('\n')
        sql_lines = []
        in_sql = False
        
        for line in lines:
            if 'SELECT' in line.upper() and not in_sql:
                in_sql = True
            if in_sql:
                sql_lines.append(line)
                if line.strip().endswith(';'):
                    break
        
        return '\n'.join(sql_lines) if sql_lines else "SELECT 1 as error;"
