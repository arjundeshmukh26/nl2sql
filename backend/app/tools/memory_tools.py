"""
Memory retrieval tools for context-aware agentic responses
"""

from typing import List, Any, Dict, Optional
from .base_tool import BaseTool, ToolParameter, ToolResult
from ..memory_store import get_conversation_memory
import logging

logger = logging.getLogger(__name__)


class GetConversationContextTool(BaseTool):
    """Tool to retrieve recent conversation context for follow-up queries"""
    
    @property
    def name(self) -> str:
        return "get_conversation_context"
    
    @property
    def description(self) -> str:
        return """Retrieves recent conversation history and context from memory. 
        Use this tool FIRST for follow-up questions, clarifications, or when the user references 
        something discussed earlier (e.g., 'what about...', 'more details on...', 'the same but...', 
        'earlier you mentioned...', 'that query', 'those results'). 
        This helps you understand context without re-running expensive database queries."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="num_exchanges",
                type="integer",
                description="Number of recent exchanges to retrieve (1-5). Default is 3.",
                required=False,
                default=3
            ),
            ToolParameter(
                name="include_sql",
                type="boolean",
                description="Whether to include SQL queries from previous exchanges",
                required=False,
                default=True
            ),
            ToolParameter(
                name="include_results_summary",
                type="boolean",
                description="Whether to include result summaries from previous exchanges",
                required=False,
                default=True
            )
        ]
    
    async def execute(self, num_exchanges: int = 3, include_sql: bool = True, 
                     include_results_summary: bool = True) -> ToolResult:
        try:
            memory = get_conversation_memory()
            
            # Clamp num_exchanges between 1 and 5
            num_exchanges = max(1, min(5, num_exchanges))
            
            exchanges = list(memory.exchanges)[-num_exchanges:]
            
            if not exchanges:
                return ToolResult(
                    success=True,
                    data={
                        "has_context": False,
                        "message": "No previous conversation context available. This is a fresh conversation.",
                        "exchanges": [],
                        "tables_discussed": [],
                        "memory_state": memory.get_memory_state()
                    }
                )
            
            # Format exchanges for the LLM
            formatted_exchanges = []
            for i, exchange in enumerate(exchanges, 1):
                exchange_data = {
                    "exchange_number": i,
                    "user_query": exchange.user_query,
                    "assistant_response_summary": exchange.assistant_response[:500] if exchange.assistant_response else None,
                    "timestamp": exchange.timestamp.isoformat()
                }
                
                if include_sql and exchange.sql_generated:
                    exchange_data["sql_used"] = exchange.sql_generated
                
                if include_results_summary and exchange.results_summary:
                    exchange_data["results_summary"] = exchange.results_summary
                
                if exchange.visualization_type:
                    exchange_data["visualization_used"] = exchange.visualization_type
                
                if exchange.tools_used:
                    exchange_data["tools_used"] = exchange.tools_used
                
                formatted_exchanges.append(exchange_data)
            
            # Get additional context
            tables_discussed = memory.get_mentioned_tables()
            last_exchange = memory.get_last_exchange()
            
            return ToolResult(
                success=True,
                data={
                    "has_context": True,
                    "exchange_count": len(formatted_exchanges),
                    "exchanges": formatted_exchanges,
                    "tables_discussed": tables_discussed,
                    "last_query": last_exchange.user_query if last_exchange else None,
                    "last_sql": last_exchange.sql_generated if last_exchange else None,
                    "memory_state": memory.get_memory_state()
                },
                metadata={
                    "total_exchanges_in_memory": len(memory.exchanges),
                    "max_memory_capacity": memory.max_exchanges
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving conversation context: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to retrieve conversation context: {str(e)}"
            )


class SearchConversationMemoryTool(BaseTool):
    """Tool to search for specific topics in conversation history"""
    
    @property
    def name(self) -> str:
        return "search_conversation_memory"
    
    @property
    def description(self) -> str:
        return """Searches conversation memory for specific keywords or topics. 
        Use this when the user asks about something specific that may have been discussed before, 
        or when you need to find relevant context about a particular topic."""
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="keywords",
                type="string",
                description="Comma-separated keywords to search for in conversation history",
                required=True
            )
        ]
    
    async def execute(self, keywords: str) -> ToolResult:
        try:
            memory = get_conversation_memory()
            
            # Split keywords
            keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
            
            if not keyword_list:
                return ToolResult(
                    success=False,
                    error="No valid keywords provided"
                )
            
            # Search for matching exchanges
            matching_exchanges = memory.search_context(keyword_list)
            
            # Format results
            results = []
            for exchange in matching_exchanges:
                results.append({
                    "user_query": exchange.user_query,
                    "response_summary": exchange.assistant_response[:300] if exchange.assistant_response else None,
                    "sql_used": exchange.sql_generated,
                    "timestamp": exchange.timestamp.isoformat()
                })
            
            # Check if any keyword was discussed
            topics_found = {kw: memory.has_discussed(kw) for kw in keyword_list}
            
            return ToolResult(
                success=True,
                data={
                    "keywords_searched": keyword_list,
                    "matches_found": len(results),
                    "matching_exchanges": results,
                    "topics_in_memory": topics_found,
                    "tables_discussed": memory.get_mentioned_tables()
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching conversation memory: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to search conversation memory: {str(e)}"
            )
