"""
Intelligent Query Classifier - Determines query complexity and required approach
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"           # Can be answered from memory or simple SQL
    MODERATE = "moderate"       # Needs SQL generation but straightforward
    COMPLEX = "complex"         # Needs multi-step investigation with tools


class QueryIntent(Enum):
    """Query intent types"""
    RETRIEVAL = "retrieval"         # Simple data retrieval
    AGGREGATION = "aggregation"     # Counts, sums, averages
    COMPARISON = "comparison"       # Compare categories/time periods
    TREND_ANALYSIS = "trend"        # Time series, trends
    ANOMALY_DETECTION = "anomaly"   # Find unusual patterns
    CORRELATION = "correlation"     # Relationships between variables
    FOLLOW_UP = "follow_up"         # References previous query
    CLARIFICATION = "clarification" # Asking for more details
    EXPLORATION = "exploration"     # Open-ended data exploration


@dataclass
class QueryClassification:
    """Result of query classification"""
    complexity: QueryComplexity
    intent: QueryIntent
    requires_tools: bool
    requires_visualization: bool
    suggested_viz_type: Optional[str]
    confidence: float
    reasoning: str
    referenced_context: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "complexity": self.complexity.value,
            "intent": self.intent.value,
            "requires_tools": self.requires_tools,
            "requires_visualization": self.requires_visualization,
            "suggested_viz_type": self.suggested_viz_type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "referenced_context": self.referenced_context
        }


class QueryClassifier:
    """
    Classifies queries to determine the optimal processing approach.
    Decides whether to use tools/agents or respond directly.
    """
    
    # Keywords indicating different intents
    ANOMALY_KEYWORDS = [
        'anomaly', 'anomalies', 'unusual', 'strange', 'weird', 'outlier',
        'abnormal', 'irregular', 'suspicious', 'unexpected', 'deviation',
        'error', 'wrong', 'fraud', 'detect', 'find issues', 'problems'
    ]
    
    TREND_KEYWORDS = [
        'trend', 'over time', 'growth', 'decline', 'change', 'evolution',
        'monthly', 'weekly', 'daily', 'yearly', 'quarterly', 'historical',
        'progress', 'trajectory', 'pattern over'
    ]
    
    COMPARISON_KEYWORDS = [
        'compare', 'versus', 'vs', 'difference', 'between', 'against',
        'better', 'worse', 'higher', 'lower', 'more than', 'less than',
        'top', 'bottom', 'best', 'worst', 'ranking', 'rank'
    ]
    
    AGGREGATION_KEYWORDS = [
        'total', 'sum', 'average', 'mean', 'count', 'how many', 'how much',
        'maximum', 'minimum', 'max', 'min', 'overall', 'aggregate'
    ]
    
    EXPLORATION_KEYWORDS = [
        'analyze', 'investigate', 'explore', 'understand', 'insight',
        'tell me about', 'what can you tell', 'deep dive', 'comprehensive',
        'full analysis', 'everything about', 'overview'
    ]
    
    FOLLOW_UP_KEYWORDS = [
        'that', 'those', 'it', 'them', 'this', 'these', 'same',
        'previous', 'last', 'earlier', 'mentioned', 'above',
        'more about', 'drill down', 'expand on', 'why', 'how come'
    ]
    
    SIMPLE_PATTERNS = [
        r'^(show|list|get|give me|what (is|are)|display)\s+(the\s+)?\w+$',
        r'^how many\s+\w+\??$',
        r'^what\'?s the (total|count|average)',
    ]
    
    def __init__(self):
        logger.info("🧠 Query Classifier initialized")
    
    def classify(
        self, 
        query: str, 
        has_context: bool = False,
        last_query: Optional[str] = None
    ) -> QueryClassification:
        """
        Classify a query to determine processing approach.
        
        Args:
            query: The user's query
            has_context: Whether there's previous conversation context
            last_query: The previous query (if any)
        
        Returns:
            QueryClassification with complexity, intent, and recommendations
        """
        query_lower = query.lower().strip()
        
        # Check for follow-up references
        is_follow_up = self._is_follow_up(query_lower, has_context)
        
        # Determine intent
        intent = self._determine_intent(query_lower, is_follow_up)
        
        # Determine complexity
        complexity = self._determine_complexity(query_lower, intent)
        
        # Determine if tools are needed
        requires_tools = self._requires_tools(complexity, intent)
        
        # Determine visualization type
        viz_type = self._suggest_visualization(intent, query_lower)
        
        # Calculate confidence
        confidence = self._calculate_confidence(query_lower, intent)
        
        # Build reasoning
        reasoning = self._build_reasoning(complexity, intent, is_follow_up, requires_tools)
        
        classification = QueryClassification(
            complexity=complexity,
            intent=intent,
            requires_tools=requires_tools,
            requires_visualization=True,  # Always include visualization
            suggested_viz_type=viz_type,
            confidence=confidence,
            reasoning=reasoning,
            referenced_context=is_follow_up
        )
        
        logger.info(f"🏷️ Query classified: {classification.to_dict()}")
        return classification
    
    def _is_follow_up(self, query: str, has_context: bool) -> bool:
        """Check if query is a follow-up to previous conversation"""
        if not has_context:
            return False
        
        # Check for follow-up indicators
        for keyword in self.FOLLOW_UP_KEYWORDS:
            if keyword in query:
                return True
        
        # Very short queries are often follow-ups
        if len(query.split()) <= 3 and has_context:
            return True
        
        return False
    
    def _determine_intent(self, query: str, is_follow_up: bool) -> QueryIntent:
        """Determine the primary intent of the query"""
        
        if is_follow_up:
            # Check if it's a clarification or drilling down
            if any(kw in query for kw in ['why', 'how come', 'explain', 'more detail']):
                return QueryIntent.CLARIFICATION
            return QueryIntent.FOLLOW_UP
        
        # Check for exploration/analysis queries
        if any(kw in query for kw in self.EXPLORATION_KEYWORDS):
            return QueryIntent.EXPLORATION
        
        # Check for anomaly detection
        if any(kw in query for kw in self.ANOMALY_KEYWORDS):
            return QueryIntent.ANOMALY_DETECTION
        
        # Check for trend analysis
        if any(kw in query for kw in self.TREND_KEYWORDS):
            return QueryIntent.TREND_ANALYSIS
        
        # Check for comparison
        if any(kw in query for kw in self.COMPARISON_KEYWORDS):
            return QueryIntent.COMPARISON
        
        # Check for aggregation
        if any(kw in query for kw in self.AGGREGATION_KEYWORDS):
            return QueryIntent.AGGREGATION
        
        # Check for correlation
        if any(kw in query for kw in ['relationship', 'correlation', 'relate', 'affect', 'impact']):
            return QueryIntent.CORRELATION
        
        # Default to retrieval
        return QueryIntent.RETRIEVAL
    
    def _determine_complexity(self, query: str, intent: QueryIntent) -> QueryComplexity:
        """Determine query complexity based on intent and query structure"""
        
        # Simple intents
        if intent in [QueryIntent.RETRIEVAL, QueryIntent.AGGREGATION, QueryIntent.FOLLOW_UP]:
            # Check if it matches simple patterns
            for pattern in self.SIMPLE_PATTERNS:
                if re.match(pattern, query, re.IGNORECASE):
                    return QueryComplexity.SIMPLE
            return QueryComplexity.MODERATE
        
        # Moderate intents
        if intent in [QueryIntent.COMPARISON, QueryIntent.CLARIFICATION]:
            return QueryComplexity.MODERATE
        
        # Complex intents
        if intent in [QueryIntent.EXPLORATION, QueryIntent.ANOMALY_DETECTION, 
                      QueryIntent.TREND_ANALYSIS, QueryIntent.CORRELATION]:
            # Check query length and keywords for actual complexity
            word_count = len(query.split())
            if word_count < 6 and intent != QueryIntent.EXPLORATION:
                return QueryComplexity.MODERATE
            return QueryComplexity.COMPLEX
        
        return QueryComplexity.MODERATE
    
    def _requires_tools(self, complexity: QueryComplexity, intent: QueryIntent) -> bool:
        """Determine if tools/agents are needed"""
        
        # Simple queries don't need tools
        if complexity == QueryComplexity.SIMPLE:
            return False
        
        # Complex exploration and anomaly detection need tools
        if intent in [QueryIntent.EXPLORATION, QueryIntent.ANOMALY_DETECTION]:
            return True
        
        # Complex queries need tools
        if complexity == QueryComplexity.COMPLEX:
            return True
        
        # Moderate queries might need tools for certain intents
        if complexity == QueryComplexity.MODERATE:
            if intent in [QueryIntent.TREND_ANALYSIS, QueryIntent.CORRELATION]:
                return True
        
        return False
    
    def _suggest_visualization(self, intent: QueryIntent, query: str) -> str:
        """Suggest appropriate visualization type based on intent"""
        
        # Time-based queries → line chart
        if intent == QueryIntent.TREND_ANALYSIS:
            return "line"
        
        # Comparisons → bar chart
        if intent == QueryIntent.COMPARISON:
            return "bar"
        
        # Proportions/distributions
        if any(kw in query for kw in ['distribution', 'breakdown', 'percentage', 'share', 'proportion']):
            return "pie"
        
        # Correlations → scatter
        if intent == QueryIntent.CORRELATION:
            return "scatter"
        
        # Anomalies → usually bar or line depending on context
        if intent == QueryIntent.ANOMALY_DETECTION:
            if any(kw in query for kw in ['time', 'daily', 'monthly', 'trend']):
                return "line"
            return "bar"
        
        # Aggregations
        if intent == QueryIntent.AGGREGATION:
            if any(kw in query for kw in ['by', 'per', 'each', 'group']):
                return "bar"
            return "bar"  # Default for aggregations
        
        # Default
        return "bar"
    
    def _calculate_confidence(self, query: str, intent: QueryIntent) -> float:
        """Calculate confidence score for classification"""
        base_confidence = 0.7
        
        # Strong keyword matches increase confidence
        keyword_lists = {
            QueryIntent.ANOMALY_DETECTION: self.ANOMALY_KEYWORDS,
            QueryIntent.TREND_ANALYSIS: self.TREND_KEYWORDS,
            QueryIntent.COMPARISON: self.COMPARISON_KEYWORDS,
            QueryIntent.AGGREGATION: self.AGGREGATION_KEYWORDS,
            QueryIntent.EXPLORATION: self.EXPLORATION_KEYWORDS,
        }
        
        if intent in keyword_lists:
            matches = sum(1 for kw in keyword_lists[intent] if kw in query)
            base_confidence += min(0.2, matches * 0.05)
        
        # Longer queries typically have clearer intent
        word_count = len(query.split())
        if word_count > 5:
            base_confidence += 0.05
        
        return min(0.95, base_confidence)
    
    def _build_reasoning(
        self, 
        complexity: QueryComplexity, 
        intent: QueryIntent, 
        is_follow_up: bool,
        requires_tools: bool
    ) -> str:
        """Build human-readable reasoning for classification"""
        parts = []
        
        parts.append(f"Query classified as {complexity.value} complexity with {intent.value} intent.")
        
        if is_follow_up:
            parts.append("Detected as follow-up to previous conversation.")
        
        if requires_tools:
            parts.append("Multi-step analysis with tools recommended.")
        else:
            parts.append("Direct response without tools recommended for efficiency.")
        
        return " ".join(parts)


# Global classifier instance
_query_classifier: Optional[QueryClassifier] = None


def get_query_classifier() -> QueryClassifier:
    """Get or create the global query classifier instance"""
    global _query_classifier
    if _query_classifier is None:
        _query_classifier = QueryClassifier()
    return _query_classifier
