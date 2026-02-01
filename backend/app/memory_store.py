"""
Conversation Memory Store - Rolling buffer of last N chats for context-aware responses
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a single chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ChatExchange:
    """Represents a complete user-assistant exchange"""
    user_query: str
    assistant_response: str
    sql_generated: Optional[str] = None
    results_summary: Optional[Dict[str, Any]] = None
    visualization_type: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_query": self.user_query,
            "assistant_response": self.assistant_response,
            "sql_generated": self.sql_generated,
            "results_summary": self.results_summary,
            "visualization_type": self.visualization_type,
            "tools_used": self.tools_used,
            "timestamp": self.timestamp.isoformat()
        }
    
    def get_context_summary(self) -> str:
        """Get a concise summary for context"""
        summary = f"Q: {self.user_query[:100]}..."
        if self.sql_generated:
            summary += f"\nSQL: {self.sql_generated[:100]}..."
        if self.results_summary:
            summary += f"\nResults: {self.results_summary.get('row_count', 0)} rows"
        return summary


class ConversationMemory:
    """
    Rolling memory buffer that maintains the last N chat exchanges.
    Provides context for follow-up queries and avoids redundant questions.
    """
    
    def __init__(self, max_exchanges: int = 5):
        self.max_exchanges = max_exchanges
        self.exchanges: deque[ChatExchange] = deque(maxlen=max_exchanges)
        self.schema_cache: Optional[Dict[str, Any]] = None
        self.schema_cache_time: Optional[datetime] = None
        logger.info(f"📚 Initialized conversation memory with {max_exchanges} exchange buffer")
    
    def add_exchange(
        self,
        user_query: str,
        assistant_response: str,
        sql_generated: Optional[str] = None,
        results_summary: Optional[Dict[str, Any]] = None,
        visualization_type: Optional[str] = None,
        tools_used: Optional[List[str]] = None
    ) -> None:
        """Add a new exchange to memory (automatically discards oldest if at capacity)"""
        exchange = ChatExchange(
            user_query=user_query,
            assistant_response=assistant_response,
            sql_generated=sql_generated,
            results_summary=results_summary,
            visualization_type=visualization_type,
            tools_used=tools_used or []
        )
        self.exchanges.append(exchange)
        logger.info(f"💾 Added exchange to memory. Buffer: {len(self.exchanges)}/{self.max_exchanges}")
    
    def get_recent_context(self, num_exchanges: int = 3) -> str:
        """Get formatted context from recent exchanges"""
        if not self.exchanges:
            return "No previous conversation context."
        
        recent = list(self.exchanges)[-num_exchanges:]
        context_parts = ["## Recent Conversation Context:"]
        
        for i, exchange in enumerate(recent, 1):
            context_parts.append(f"\n### Exchange {i}:")
            context_parts.append(f"User: {exchange.user_query}")
            if exchange.sql_generated:
                context_parts.append(f"SQL Used: {exchange.sql_generated[:200]}...")
            if exchange.results_summary:
                context_parts.append(f"Results: {exchange.results_summary}")
            context_parts.append(f"Response: {exchange.assistant_response[:300]}...")
        
        return "\n".join(context_parts)
    
    def get_last_exchange(self) -> Optional[ChatExchange]:
        """Get the most recent exchange"""
        return self.exchanges[-1] if self.exchanges else None
    
    def get_last_sql(self) -> Optional[str]:
        """Get the SQL from the last exchange"""
        last = self.get_last_exchange()
        return last.sql_generated if last else None
    
    def get_last_results(self) -> Optional[Dict[str, Any]]:
        """Get results summary from the last exchange"""
        last = self.get_last_exchange()
        return last.results_summary if last else None
    
    def search_context(self, keywords: List[str]) -> List[ChatExchange]:
        """Search memory for exchanges containing keywords"""
        matches = []
        for exchange in self.exchanges:
            query_lower = exchange.user_query.lower()
            if any(kw.lower() in query_lower for kw in keywords):
                matches.append(exchange)
        return matches
    
    def has_discussed(self, topic: str) -> bool:
        """Check if a topic was discussed in recent memory"""
        topic_lower = topic.lower()
        for exchange in self.exchanges:
            if topic_lower in exchange.user_query.lower():
                return True
            if exchange.assistant_response and topic_lower in exchange.assistant_response.lower():
                return True
        return False
    
    def get_mentioned_tables(self) -> List[str]:
        """Extract table names mentioned in recent conversations"""
        tables = set()
        table_keywords = ['from', 'join', 'table']
        
        for exchange in self.exchanges:
            if exchange.sql_generated:
                sql_upper = exchange.sql_generated.upper()
                # Simple extraction of table names after FROM and JOIN
                words = exchange.sql_generated.split()
                for i, word in enumerate(words):
                    if word.upper() in ['FROM', 'JOIN'] and i + 1 < len(words):
                        table = words[i + 1].strip('(),;').lower()
                        if table and not table.startswith('('):
                            tables.add(table)
        
        return list(tables)
    
    def cache_schema(self, schema: Dict[str, Any]) -> None:
        """Cache the database schema"""
        self.schema_cache = schema
        self.schema_cache_time = datetime.now()
        logger.info("📋 Schema cached in memory")
    
    def get_cached_schema(self) -> Optional[Dict[str, Any]]:
        """Get cached schema if available and fresh (< 5 minutes old)"""
        if self.schema_cache and self.schema_cache_time:
            age = (datetime.now() - self.schema_cache_time).seconds
            if age < 300:  # 5 minutes
                logger.info(f"📋 Using cached schema (age: {age}s)")
                return self.schema_cache
        return None
    
    def clear(self) -> None:
        """Clear all memory"""
        self.exchanges.clear()
        self.schema_cache = None
        self.schema_cache_time = None
        logger.info("🧹 Memory cleared")
    
    def get_memory_state(self) -> Dict[str, Any]:
        """Get current memory state for debugging"""
        return {
            "exchange_count": len(self.exchanges),
            "max_exchanges": self.max_exchanges,
            "has_schema_cache": self.schema_cache is not None,
            "recent_queries": [e.user_query[:50] for e in self.exchanges],
            "tables_discussed": self.get_mentioned_tables()
        }


# Global memory instance
_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    """Get or create the global conversation memory instance"""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory(max_exchanges=5)
    return _conversation_memory


def reset_conversation_memory() -> None:
    """Reset the global conversation memory"""
    global _conversation_memory
    if _conversation_memory:
        _conversation_memory.clear()
    _conversation_memory = ConversationMemory(max_exchanges=5)
