"""
Automatic Visualization Selector - Chooses optimal chart type based on data characteristics
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

logger = logging.getLogger(__name__)


@dataclass
class VisualizationConfig:
    """Configuration for a visualization"""
    chart_type: str
    x_field: str
    y_field: str
    title: str
    x_label: str
    y_label: str
    confidence: float
    reasoning: str
    additional_config: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "chart_type": self.chart_type,
            "x_field": self.x_field,
            "y_field": self.y_field,
            "title": self.title,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }
        if self.additional_config:
            result["additional_config"] = self.additional_config
        return result


class VisualizationSelector:
    """
    Automatically selects the optimal visualization type based on:
    - Data structure (columns, types)
    - Data patterns (time series, categorical, numeric)
    - Query intent
    - Row count
    """
    
    # Date/time column indicators
    DATE_PATTERNS = [
        'date', 'time', 'datetime', 'timestamp', 'created', 'updated',
        'day', 'month', 'year', 'week', 'quarter', 'period', '_at'
    ]
    
    # Categorical column indicators
    CATEGORY_PATTERNS = [
        'name', 'type', 'category', 'status', 'region', 'country', 'city',
        'product', 'customer', 'user', 'department', 'group', 'class', '_id'
    ]
    
    # Numeric/value column indicators
    NUMERIC_PATTERNS = [
        'amount', 'total', 'sum', 'count', 'price', 'cost', 'revenue',
        'quantity', 'value', 'number', 'rate', 'percentage', 'avg', 'average'
    ]
    
    def __init__(self):
        logger.info("📊 Visualization Selector initialized")
    
    def select_visualization(
        self,
        data: List[Dict[str, Any]],
        query: str = "",
        suggested_type: Optional[str] = None
    ) -> VisualizationConfig:
        """
        Select the optimal visualization for the given data.
        
        Args:
            data: The query result data
            query: The original user query (for context)
            suggested_type: Pre-suggested type from query classifier
        
        Returns:
            VisualizationConfig with chart configuration
        """
        if not data:
            return self._default_config("No data available")
        
        # Analyze data structure
        columns = list(data[0].keys())
        row_count = len(data)
        
        # Detect column types
        date_cols = self._find_columns_by_pattern(columns, self.DATE_PATTERNS)
        category_cols = self._find_columns_by_pattern(columns, self.CATEGORY_PATTERNS)
        numeric_cols = self._find_columns_by_pattern(columns, self.NUMERIC_PATTERNS)
        
        # Also detect by actual values
        detected_types = self._detect_column_types(data, columns)
        
        # Merge detections
        for col, col_type in detected_types.items():
            if col_type == 'date' and col not in date_cols:
                date_cols.append(col)
            elif col_type == 'numeric' and col not in numeric_cols:
                numeric_cols.append(col)
            elif col_type == 'category' and col not in category_cols:
                category_cols.append(col)
        
        logger.info(f"📊 Column analysis: dates={date_cols}, categories={category_cols}, numeric={numeric_cols}")
        
        # Decision logic
        viz_config = self._select_chart_type(
            data=data,
            columns=columns,
            date_cols=date_cols,
            category_cols=category_cols,
            numeric_cols=numeric_cols,
            row_count=row_count,
            query=query,
            suggested_type=suggested_type
        )
        
        logger.info(f"📈 Selected visualization: {viz_config.chart_type} - {viz_config.reasoning}")
        return viz_config
    
    def _find_columns_by_pattern(self, columns: List[str], patterns: List[str]) -> List[str]:
        """Find columns matching any of the patterns"""
        matches = []
        for col in columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in patterns):
                matches.append(col)
        return matches
    
    def _detect_column_types(self, data: List[Dict], columns: List[str]) -> Dict[str, str]:
        """Detect column types by examining actual values"""
        types = {}
        sample = data[:min(10, len(data))]  # Check first 10 rows
        
        for col in columns:
            values = [row.get(col) for row in sample if row.get(col) is not None]
            
            if not values:
                continue
            
            # Check for dates
            if self._is_date_column(values):
                types[col] = 'date'
            # Check for numeric
            elif self._is_numeric_column(values):
                types[col] = 'numeric'
            # Check for categorical (limited unique values)
            elif self._is_categorical_column(values, len(data)):
                types[col] = 'category'
            else:
                types[col] = 'text'
        
        return types
    
    def _is_date_column(self, values: List) -> bool:
        """Check if values appear to be dates"""
        date_count = 0
        for val in values:
            if val is None:
                continue
            str_val = str(val)
            # Check for ISO date format or common date patterns
            if re.match(r'\d{4}-\d{2}-\d{2}', str_val):
                date_count += 1
            elif re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', str_val):
                date_count += 1
            elif 'T' in str_val and ':' in str_val:  # ISO datetime
                date_count += 1
        
        return date_count > len(values) * 0.5
    
    def _is_numeric_column(self, values: List) -> bool:
        """Check if values are numeric"""
        numeric_count = 0
        for val in values:
            if val is None:
                continue
            if isinstance(val, (int, float)):
                numeric_count += 1
            elif isinstance(val, str):
                try:
                    float(val.replace(',', ''))
                    numeric_count += 1
                except (ValueError, AttributeError):
                    pass
        
        return numeric_count > len(values) * 0.7
    
    def _is_categorical_column(self, values: List, total_rows: int) -> bool:
        """Check if column appears categorical (limited unique values)"""
        unique_values = set(str(v) for v in values if v is not None)
        # Categorical if unique values are much less than total rows
        return len(unique_values) < min(20, total_rows * 0.5)
    
    def _select_chart_type(
        self,
        data: List[Dict],
        columns: List[str],
        date_cols: List[str],
        category_cols: List[str],
        numeric_cols: List[str],
        row_count: int,
        query: str,
        suggested_type: Optional[str]
    ) -> VisualizationConfig:
        """Select the optimal chart type based on data characteristics"""
        
        query_lower = query.lower()
        
        # RULE 1: Time series data → Line chart
        if date_cols and numeric_cols:
            x_field = date_cols[0]
            y_field = numeric_cols[0] if numeric_cols else columns[1] if len(columns) > 1 else columns[0]
            
            # Check query for trend indicators
            if any(kw in query_lower for kw in ['trend', 'over time', 'growth', 'change', 'monthly', 'daily']):
                return VisualizationConfig(
                    chart_type="line",
                    x_field=x_field,
                    y_field=y_field,
                    title=self._generate_title(query, "Trend"),
                    x_label=self._format_label(x_field),
                    y_label=self._format_label(y_field),
                    confidence=0.9,
                    reasoning="Time series data detected with date column - line chart optimal for showing trends"
                )
        
        # RULE 2: Comparisons with categories → Bar chart
        if category_cols and numeric_cols:
            x_field = category_cols[0]
            y_field = numeric_cols[0]
            
            if any(kw in query_lower for kw in ['compare', 'top', 'best', 'worst', 'ranking', 'by']):
                return VisualizationConfig(
                    chart_type="bar",
                    x_field=x_field,
                    y_field=y_field,
                    title=self._generate_title(query, "Comparison"),
                    x_label=self._format_label(x_field),
                    y_label=self._format_label(y_field),
                    confidence=0.9,
                    reasoning="Categorical comparison detected - bar chart ideal for comparing values across categories"
                )
        
        # RULE 3: Proportions/distributions → Pie chart (for small datasets)
        if any(kw in query_lower for kw in ['distribution', 'breakdown', 'share', 'percentage', 'proportion']):
            if row_count <= 10 and category_cols:
                x_field = category_cols[0]
                y_field = numeric_cols[0] if numeric_cols else columns[-1]
                
                return VisualizationConfig(
                    chart_type="pie",
                    x_field=x_field,
                    y_field=y_field,
                    title=self._generate_title(query, "Distribution"),
                    x_label=self._format_label(x_field),
                    y_label=self._format_label(y_field),
                    confidence=0.85,
                    reasoning="Distribution query with limited categories - pie chart shows proportions effectively"
                )
        
        # RULE 4: Correlation/relationships → Scatter plot
        if len(numeric_cols) >= 2:
            if any(kw in query_lower for kw in ['correlation', 'relationship', 'versus', 'vs', 'affect']):
                return VisualizationConfig(
                    chart_type="scatter",
                    x_field=numeric_cols[0],
                    y_field=numeric_cols[1],
                    title=self._generate_title(query, "Correlation"),
                    x_label=self._format_label(numeric_cols[0]),
                    y_label=self._format_label(numeric_cols[1]),
                    confidence=0.85,
                    reasoning="Multiple numeric columns with correlation intent - scatter plot shows relationships"
                )
        
        # RULE 5: Histogram for distributions with numeric data
        if numeric_cols and any(kw in query_lower for kw in ['histogram', 'frequency', 'distribution of']):
            return VisualizationConfig(
                chart_type="bar",  # Histogram represented as bar
                x_field=numeric_cols[0],
                y_field="count",
                title=self._generate_title(query, "Distribution"),
                x_label=self._format_label(numeric_cols[0]),
                y_label="Frequency",
                confidence=0.8,
                reasoning="Numeric distribution query - histogram (bar chart) shows value frequencies"
            )
        
        # RULE 6: Use suggested type if provided and applicable
        if suggested_type:
            x_field = columns[0]
            y_field = columns[1] if len(columns) > 1 else columns[0]
            
            if suggested_type == "line" and date_cols:
                x_field = date_cols[0]
                y_field = numeric_cols[0] if numeric_cols else columns[-1]
            elif suggested_type in ["bar", "pie"] and category_cols:
                x_field = category_cols[0]
                y_field = numeric_cols[0] if numeric_cols else columns[-1]
            elif suggested_type == "scatter" and len(numeric_cols) >= 2:
                x_field = numeric_cols[0]
                y_field = numeric_cols[1]
            
            return VisualizationConfig(
                chart_type=suggested_type,
                x_field=x_field,
                y_field=y_field,
                title=self._generate_title(query, suggested_type.capitalize()),
                x_label=self._format_label(x_field),
                y_label=self._format_label(y_field),
                confidence=0.75,
                reasoning=f"Using suggested visualization type: {suggested_type}"
            )
        
        # DEFAULT: Bar chart (most versatile)
        x_field = category_cols[0] if category_cols else columns[0]
        y_field = numeric_cols[0] if numeric_cols else (columns[1] if len(columns) > 1 else columns[0])
        
        return VisualizationConfig(
            chart_type="bar",
            x_field=x_field,
            y_field=y_field,
            title=self._generate_title(query, "Analysis"),
            x_label=self._format_label(x_field),
            y_label=self._format_label(y_field),
            confidence=0.7,
            reasoning="Default to bar chart - versatile for most data types"
        )
    
    def _generate_title(self, query: str, prefix: str = "") -> str:
        """Generate a meaningful chart title from the query"""
        # Extract key nouns from query
        query_clean = query.strip().rstrip('?').rstrip('.')
        
        # If query is short enough, use it
        if len(query_clean) < 50:
            return f"{prefix}: {query_clean}" if prefix else query_clean
        
        # Otherwise, truncate
        return f"{prefix}: {query_clean[:45]}..." if prefix else f"{query_clean[:45]}..."
    
    def _format_label(self, field_name: str) -> str:
        """Format a field name into a readable label"""
        # Replace underscores and camelCase
        label = re.sub(r'_', ' ', field_name)
        label = re.sub(r'([a-z])([A-Z])', r'\1 \2', label)
        return label.title()
    
    def _default_config(self, reason: str) -> VisualizationConfig:
        """Return a default configuration when data is insufficient"""
        return VisualizationConfig(
            chart_type="bar",
            x_field="category",
            y_field="value",
            title="Query Results",
            x_label="Category",
            y_label="Value",
            confidence=0.5,
            reasoning=reason
        )


# Global selector instance
_visualization_selector: Optional[VisualizationSelector] = None


def get_visualization_selector() -> VisualizationSelector:
    """Get or create the global visualization selector instance"""
    global _visualization_selector
    if _visualization_selector is None:
        _visualization_selector = VisualizationSelector()
    return _visualization_selector
