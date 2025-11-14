# Complete Tool Documentation - NL2SQL Agentic Investigation Platform

## Overview
This document provides a comprehensive guide to all 22 tools available in the Agentic Database Investigation Platform. Each tool is designed to be **schema-agnostic** and works with any PostgreSQL database structure.

---

## 📊 Category 1: Database Discovery Tools (4 Tools)

### 1. Get Database Schema
**Tool Name:** `get_database_schema`

**What it does:**
Retrieves the complete database schema including all tables, columns, data types, primary keys, foreign keys, and relationships. This is the foundation for understanding any database structure.

**Example Use Case:**
"Show me all the tables in this database"

**How it works:**
1. Queries PostgreSQL's `information_schema` system catalog
2. For each table, retrieves:
   - Column names and data types
   - Nullable constraints
   - Primary key definitions
   - Foreign key relationships
3. Estimates row counts using PostgreSQL statistics (`pg_class.reltuples`)
4. Builds a complete relationship map between tables

**Logic:**
```sql
-- Gets all tables
SELECT schemaname, tablename, tableowner
FROM pg_tables 
WHERE schemaname = 'public'

-- For each table, gets column info
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = [table]

-- Gets foreign key relationships
SELECT constraint information from information_schema
```

---

### 2. Describe Table
**Tool Name:** `describe_table`

**What it does:**
Provides detailed information about a specific table including columns, constraints, indexes, statistics, and sample data. Like running `DESCRIBE` but with much more detail.

**Example Use Case:**
"Describe the sales table in detail"

**How it works:**
1. Validates table existence
2. Retrieves column metadata (types, nullability, defaults)
3. Gets all constraints (primary keys, foreign keys, unique constraints)
4. Lists all indexes with their definitions
5. Fetches PostgreSQL statistics (distinct values, common values)
6. Optionally retrieves sample rows

**Logic:**
- Uses `information_schema.columns` for column details
- Queries `information_schema.table_constraints` for constraints
- Reads `pg_indexes` for index information
- Accesses `pg_stats` for statistical data
- Executes `SELECT * FROM table LIMIT N` for samples

---

### 3. Get Table Sample Data
**Tool Name:** `get_table_sample_data`

**What it does:**
Retrieves sample rows from any table to understand actual data content and patterns. Supports column filtering and WHERE clauses.

**Example Use Case:**
"Show me 20 sample rows from the customers table"

**How it works:**
1. Validates table exists in the schema
2. Builds a SELECT query with optional:
   - Specific columns (comma-separated list)
   - WHERE clause for filtering
   - LIMIT for number of rows
3. Executes query and converts results to JSON format
4. Returns data with metadata about columns selected

**Logic:**
```sql
SELECT [columns or *] 
FROM [table_name]
WHERE [optional_where_clause]
LIMIT [limit]
```

---

### 4. Estimate Table Size
**Tool Name:** `estimate_table_size`

**What it does:**
Calculates table size estimates including row counts, disk usage, and performance characteristics. Essential for query planning and understanding data volume.

**Example Use Case:**
"How big is the transactions table?"

**How it works:**
1. Uses PostgreSQL statistics for fast estimation:
   - `pg_class.reltuples` for row count estimates
   - `pg_total_relation_size()` for total size (table + indexes)
   - `pg_relation_size()` for table size only
   - `pg_indexes_size()` for index size
2. For small tables (<100K rows), gets exact count
3. Provides per-column statistics (distinct values, null fraction, average width)

**Logic:**
- Fast: Uses database statistics (instant, no table scan)
- Accurate for small tables: Runs actual COUNT(*) when feasible
- Performance-aware: Avoids expensive operations on large tables

---

## 🔧 Category 2: SQL Execution & Validation Tools (4 Tools)

### 5. Execute SQL Query
**Tool Name:** `execute_sql_query`

**What it does:**
Safely executes SQL SELECT queries with built-in safety protections. Prevents destructive operations and automatically applies limits.

**Example Use Case:**
"Get total revenue by product"

**How it works:**
1. **Safety Validation:**
   - Blocks any non-SELECT statements (INSERT, UPDATE, DELETE, DROP)
   - Prevents SQL injection attempts
   - Checks for dangerous operations
2. **Automatic Protection:**
   - Applies LIMIT if not specified (default 1000 rows)
   - Sets query timeout
   - Prevents Cartesian products
3. **Execution:**
   - Runs query with timing
   - Optionally includes EXPLAIN plan
   - Returns results as JSON

**Logic:**
```python
# Safety check
if not is_safe_sql(query):
    return error

# Add limits
safe_query = add_safety_limits(query)

# Execute with timing
start = time.time()
results = execute(safe_query)
execution_time = time.time() - start

return results + execution_time
```

---

### 6. Validate SQL Syntax
**Tool Name:** `validate_sql_syntax`

**What it does:**
Validates SQL query syntax and safety WITHOUT executing it. Provides warnings and suggestions for improvement.

**Example Use Case:**
"Check if this query is valid before running it"

**How it works:**
1. **Safety Checks:**
   - Verifies only SELECT statements
   - Checks for balanced parentheses
   - Identifies dangerous patterns
2. **Syntax Validation:**
   - Uses PostgreSQL's EXPLAIN (without ANALYZE) to validate syntax
   - No actual execution, no data modification
3. **Quality Suggestions:**
   - Warns about SELECT * without LIMIT
   - Flags JOIN without ON clause
   - Suggests LIMIT for ORDER BY queries

**Logic:**
- Uses EXPLAIN to validate without execution
- Pattern matching for common issues
- Returns validation result with warnings/suggestions

---

### 7. Explain Query Plan
**Tool Name:** `explain_query_plan`

**What it does:**
Retrieves detailed execution plan for a query to understand performance characteristics and optimization opportunities.

**Example Use Case:**
"Why is this query slow?"

**How it works:**
1. **Plan Generation:**
   - Runs `EXPLAIN (FORMAT JSON, VERBOSE, BUFFERS)` 
   - Optionally adds ANALYZE for real execution metrics
2. **Analysis:**
   - Extracts node types (Seq Scan, Index Scan, Hash Join, etc.)
   - Identifies total cost and estimated rows
   - If ANALYZE: captures actual time and row counts
3. **Expensive Operation Detection:**
   - Finds operations above cost threshold
   - Highlights potential bottlenecks

**Logic:**
```sql
EXPLAIN (FORMAT JSON, VERBOSE, BUFFERS, ANALYZE?) 
[your_query]
```
Returns: Plan tree with costs, times, row estimates

---

### 8. Optimize Query
**Tool Name:** `optimize_query`

**What it does:**
Analyzes a SQL query and suggests performance optimizations with impact ratings.

**Example Use Case:**
"How can I make this query faster?"

**How it works:**
1. **Pattern Analysis:**
   - SELECT * usage → Suggest specific columns
   - ORDER BY without LIMIT → Add LIMIT
   - JOIN without ON → Fix Cartesian product
   - Functions in WHERE → Suggests functional indexes
   - LIKE with leading % → Cannot use indexes
   - IN with subquery → Suggests EXISTS or JOIN
2. **Execution Plan Analysis:**
   - Sequential scans → Suggest indexes
   - Expensive nested loops → Suggest hash join
   - Expensive sorts → Suggest sorted indexes
3. **Impact Rating:**
   - Critical: Major performance issues
   - High: Significant improvement possible
   - Medium: Moderate optimization
   - Low: Minor improvement

**Logic:**
- Static analysis via regex pattern matching
- Dynamic analysis via EXPLAIN plan
- Prioritizes suggestions by impact

---

## 📈 Category 3: Statistical Analysis Tools (4 Tools)

### 9. Get Column Statistics
**Tool Name:** `get_column_statistics`

**What it does:**
Provides comprehensive statistical analysis of any column including distribution, data quality, and type-specific metrics.

**Example Use Case:**
"Analyze the price column distribution"

**How it works:**
1. **Basic Statistics (all types):**
   - Total rows, null count, null percentage
   - Distinct count, uniqueness ratio
2. **Numeric Columns:**
   - Min, max, mean, median, std deviation
   - Quartiles (Q1, Q3)
   - IQR and outlier detection
3. **Text Columns:**
   - Min/max/average length
   - Empty string count
4. **Date Columns:**
   - Earliest and latest dates
   - Date range in days
5. **Value Distribution:**
   - For low cardinality: full distribution
   - For high cardinality: top 10 values

**Logic:**
```sql
-- Numeric example
SELECT 
    MIN(column), MAX(column), AVG(column),
    STDDEV(column),
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY column) as q1,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY column) as median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY column) as q3
FROM table
```

---

### 10. Detect Data Anomalies
**Tool Name:** `detect_data_anomalies`

**What it does:**
Identifies anomalies, outliers, and unusual patterns using statistical methods (Z-score, temporal spikes, data quality issues).

**Example Use Case:**
"Find unusual values in the revenue column"

**How it works:**
1. **Statistical Outliers (Z-score method):**
   ```
   Z-score = (value - mean) / std_deviation
   Outlier if |Z-score| > threshold (default 2.5)
   ```
2. **Temporal Spikes:**
   - Calculates daily/weekly averages
   - Detects >200% day-to-day changes
   - Identifies sudden drops or spikes
3. **Data Quality Anomalies:**
   - Duplicate rows
   - High null percentages (>50%)
4. **Severity Scoring:**
   - High: >10 outliers or critical issues
   - Medium: <10 outliers or moderate issues
   - Low: Minor deviations

**Logic:**
```sql
WITH stats AS (
    SELECT AVG(column) as mean, STDDEV(column) as std
    FROM table
)
SELECT *, ABS((column - mean) / std) as z_score
FROM table, stats
WHERE ABS((column - mean) / std) > 2.5
```

---

### 11. Find Correlations
**Tool Name:** `find_correlations`

**What it does:**
Calculates statistical correlations between numeric columns to identify relationships and dependencies.

**Example Use Case:**
"Find columns that correlate with sales"

**How it works:**
1. **Identifies numeric columns** (if not specified)
2. **Calculates pairwise correlations:**
   - Uses PostgreSQL's CORR() function
   - Pearson correlation coefficient: -1 to +1
3. **Filters by minimum threshold** (default 0.3)
4. **Classifies strength:**
   - Very Strong: |r| ≥ 0.8
   - Strong: |r| ≥ 0.6
   - Moderate: |r| ≥ 0.4
   - Weak: |r| ≥ 0.3
5. **Determines direction:**
   - Positive: Variables increase together
   - Negative: One increases, other decreases

**Logic:**
```sql
SELECT 
    CORR(column1, column2) as correlation_coefficient,
    COUNT(*) as sample_size
FROM table
WHERE column1 IS NOT NULL AND column2 IS NOT NULL
```

---

### 12. Analyze Data Quality
**Tool Name:** `analyze_data_quality`

**What it does:**
Performs comprehensive data quality analysis across all dimensions: completeness, consistency, validity, and uniqueness.

**Example Use Case:**
"Check data quality of the orders table"

**How it works:**
1. **Completeness Check:**
   - Null count and percentage per column
   - Flags non-nullable columns with nulls
2. **Uniqueness Check:**
   - Distinct value count
   - Duplicate detection
3. **Type-Specific Validity:**
   - **Text:** Empty strings, special characters
   - **Numeric:** Negative values, zeros
   - **Date:** Future dates, very old dates
4. **Quality Scoring:**
   - Column score = (completeness + uniqueness) / 2
   - Overall score = average of all columns
5. **Quality Grading:**
   - Excellent: ≥90%
   - Good: ≥80%
   - Fair: ≥70%
   - Poor: <70%

**Logic:**
For each column:
```sql
-- Completeness
SELECT COUNT(*) - COUNT(column) as null_count FROM table

-- Uniqueness
SELECT COUNT(DISTINCT column) FROM table

-- Validity (example for dates)
SELECT COUNT(*) FROM table WHERE column > CURRENT_DATE
```

---

## 🔍 Category 4: Investigation Tools (3 Tools)

### 13. Generate Drill-Down Queries
**Tool Name:** `generate_drill_down_queries`

**What it does:**
Automatically generates follow-up SQL queries to investigate findings deeper, creating targeted analysis based on initial results.

**Example Use Case:**
"Revenue is down in Q3, investigate further"

**How it works:**
1. **Validates schema** (table, dimension, metric columns exist)
2. **Generates 5 types of drill-down queries:**
   
   a. **Basic Breakdown:**
   ```sql
   SELECT dimension, 
       COUNT(*), SUM(metric), AVG(metric), MIN(metric), MAX(metric)
   FROM table
   GROUP BY dimension
   ORDER BY SUM(metric) DESC
   ```
   
   b. **Top/Bottom Analysis:**
   ```sql
   (Top 5 performers)
   UNION ALL
   (Bottom 5 performers)
   ```
   
   c. **Outlier Detection:**
   - Z-score analysis by dimension
   - Finds values >1.5 std deviations
   
   d. **Time Trend Analysis:** (if date column exists)
   - Monthly breakdown by dimension
   
   e. **Comparative Analysis:**
   - Compares each dimension against overall average
   - Shows % difference from mean

**Logic:**
Dynamically constructs queries based on:
- Table schema
- Available columns
- Finding description
- Filter conditions

---

### 14. Compare Time Periods
**Tool Name:** `compare_time_periods`

**What it does:**
Compares metrics between two time periods to identify trends, performance changes, and growth/decline patterns.

**Example Use Case:**
"Compare Q1 2024 vs Q1 2023"

**How it works:**
1. **Validates** date and metric columns exist
2. **Dual Period Query:**
   ```sql
   WITH period1_data AS (
       SELECT SUM(metric), AVG(metric), COUNT(*)
       FROM table
       WHERE date BETWEEN start1 AND end1
       GROUP BY dimension?
   ),
   period2_data AS (
       -- Same for period 2
   )
   SELECT 
       period1_total, period2_total,
       period2_total - period1_total as change,
       (period2 - period1) / period1 * 100 as pct_change
   FROM period1 JOIN period2
   ```
3. **Calculates:**
   - Absolute change
   - Percentage change
   - Segments improved vs declined
4. **Summary Statistics:**
   - Overall change across all segments
   - Average percentage change
   - Count of improved/declined/unchanged

**Logic:**
- CTEs for each period
- FULL OUTER JOIN to handle missing data
- NULL coalescing for robust calculations

---

### 15. Detect Seasonal Patterns
**Tool Name:** `detect_seasonal_patterns`

**What it does:**
Analyzes time-series data to detect seasonal patterns, cyclical trends, and recurring behaviors at different granularities.

**Example Use Case:**
"Do we have seasonal sales patterns?"

**How it works:**
1. **Pattern Types:**
   - **Monthly:** Groups by month (1-12)
   - **Quarterly:** Groups by quarter (Q1-Q4)
   - **Weekly:** Groups by day of week (Sun-Sat)
   - **Daily:** Groups by hour of day (0-23)

2. **Aggregation:**
   ```sql
   SELECT 
       EXTRACT(MONTH FROM date) as month,
       AVG(metric), SUM(metric), STDDEV(metric)
   FROM table
   GROUP BY month
   ORDER BY month
   ```

3. **Pattern Analysis:**
   - Calculates coefficient of variation (CV)
   - Identifies peaks (>20% above average)
   - Identifies troughs (>20% below average)
   - Determines seasonality strength:
     * High: CV > 30%
     * Medium: CV > 15%
     * Low: CV > 5%
     * Minimal: CV ≤ 5%

**Logic:**
- Coefficient of Variation = (std_dev / mean) × 100
- Higher CV indicates stronger seasonality
- Peaks and troughs show when patterns occur

---

## 📊 Category 5: Visualization Tools (6 Tools)

### 16. Generate Chart
**Tool Name:** `generate_chart`

**What it does:**
Creates chart configuration for data visualization. Universal tool that supports 7 chart types with automatic field mapping.

**Example Use Case:**
"Create a bar chart of sales by region"

**How it works:**
1. **Accepts JSON data** (from query results)
2. **Validates chart type requirements:**
   - Bar/Line/Scatter: Need x_field and y_field
   - Pie/Donut: Need label and value fields
3. **Generates chart config:**
   ```json
   {
     "type": "bar",
     "data": [...],
     "config": {
       "x_field": "region",
       "y_field": "total_sales",
       "title": "Sales by Region",
       "x_label": "Region",
       "y_label": "Total Sales"
     }
   }
   ```
4. **Returns to frontend** for rendering with Chart.js

**Supported Types:**
- bar, line, pie, scatter, area, column, donut

**Logic:**
- Parses JSON data string
- Validates field existence
- Creates Chart.js compatible configuration

---

### 17. Suggest Visualization
**Tool Name:** `suggest_visualization`

**What it does:**
Analyzes data structure and automatically suggests the most appropriate visualization types and configurations.

**Example Use Case:**
"What's the best way to visualize this data?"

**How it works:**
1. **Data Structure Analysis:**
   - Identifies field types:
     * Numeric: int, float
     * Categorical: strings
     * Temporal: dates/timestamps (by name pattern)
2. **Suggestion Rules:**
   - **2+ numeric columns** → Scatter plot (correlation)
   - **Categorical + numeric** → Bar chart (comparison)
   - **Categorical + numeric** → Pie chart (distribution)
   - **Date + numeric** → Line chart (trend)
3. **Goal-Based Recommendations:**
   - "trend" → Line chart priority
   - "comparison" → Bar chart priority
   - "distribution" → Pie chart priority
4. **Returns ranked suggestions** with use cases

**Logic:**
```python
if numeric_fields >= 2:
    suggest scatter (correlation)
if categorical + numeric:
    suggest bar (comparison)
    suggest pie (distribution)
if date + numeric:
    suggest line (trend over time)
```

---

### 18-21. Specific Chart Generators

These four tools execute SQL queries and generate specific chart types:

#### 18. Generate Bar Chart (`generate_bar_chart`)
**Purpose:** Compare values across categories

**How it works:**
1. Executes SQL query
2. Extracts first column as X-axis (categories)
3. Extracts second column as Y-axis (values)
4. Creates bar chart config

**Example:** Revenue by product, sales by region

---

#### 19. Generate Line Chart (`generate_line_chart`)
**Purpose:** Show trends over time

**How it works:**
1. Executes SQL query (expecting time series data)
2. First column = X-axis (time/date)
3. Second column = Y-axis (metric)
4. Creates line chart config

**Example:** Monthly revenue trend, daily user count

---

#### 20. Generate Pie Chart (`generate_pie_chart`)
**Purpose:** Show proportional distribution

**How it works:**
1. Executes SQL query
2. First column = labels (categories)
3. Second column = values (proportions)
4. Creates pie chart config

**Example:** Market share, sales by category

---

#### 21. Generate Scatter Plot (`generate_scatter_plot`)
**Purpose:** Show correlation between two variables

**How it works:**
1. Executes SQL query
2. First column = X-axis
3. Second column = Y-axis
4. Creates scatter plot config

**Example:** Price vs sales, quantity vs revenue

---

## 💼 Category 6: Business Metrics Tools (2 Tools)

### 22. Get Key Business Metrics
**Tool Name:** `get_key_business_metrics`

**What it does:**
Executes predefined business intelligence queries to get essential KPIs (total revenue, sales count, average order value, top products, market performance, monthly trends).

**Example Use Case:**
"Show me the business dashboard"

**How it works:**
1. **Executes 4 key queries:**
   
   a. **Overview Metrics:**
   ```sql
   SELECT 
       COUNT(*) as total_sales,
       SUM(revenue) as total_revenue,
       AVG(revenue) as avg_order_value,
       SUM(quantity) as total_quantity
   FROM sales
   ```
   
   b. **Top 5 Products:**
   ```sql
   SELECT product_name, SUM(revenue), COUNT(*)
   FROM sales JOIN products
   GROUP BY product_name
   ORDER BY SUM(revenue) DESC
   LIMIT 5
   ```
   
   c. **Revenue by Market:**
   ```sql
   SELECT market_name, SUM(revenue), COUNT(*)
   FROM sales JOIN markets
   GROUP BY market_name
   ```
   
   d. **Monthly Trends (last 12 months):**
   ```sql
   SELECT DATE_TRUNC('month', sale_date), 
          SUM(revenue), COUNT(*)
   FROM sales
   WHERE sale_date >= CURRENT_DATE - INTERVAL '12 months'
   GROUP BY month
   ```

2. **Generates summary** with key highlights

**Note:** This tool uses hardcoded table/column names for a specific schema (sales, products, markets). Can be adapted for other schemas.

---

### 23. Generate Business Summary (Tool #23)
**Tool Name:** `generate_business_summary`

**What it does:**
Creates a comprehensive business performance report with metrics, insights, trends, and recommendations.

**Example Use Case:**
"Give me an executive summary"

**How it works:**
1. **Calls GetKeyBusinessMetricsTool** internally
2. **Generates insights:**
   - Total revenue and sales count
   - Top product and its market share
   - Top market performance
   - Month-over-month growth rate
3. **Creates recommendations:**
   - Focus areas based on top performers
   - Market expansion suggestions
   - Trend analysis advice
   - Strategies to improve AOV
4. **Formats as executive summary** with emojis and clear sections

**Logic:**
```python
metrics = get_key_business_metrics()

insights = []
if top_product_revenue > 0:
    share = (top_product / total_revenue) * 100
    insights.append(f"Top Product: {name} ({share}%)")

if recent_month_revenue > previous_month:
    growth = (recent - previous) / previous * 100
    insights.append(f"Growing: {growth}% MoM")

return {
    executive_summary,
    key_insights,
    top_performers,
    recommendations
}
```

---

## 🚨 Category 7: Specialized Anomaly Detection Tools (3 Tools)

### 24. Detect Revenue Anomalies (Tool #24 in implementation)
**Tool Name:** `detect_revenue_anomalies`

**What it does:**
Detects unusual revenue patterns and outliers using statistical analysis (Z-score method).

**Example Use Case:**
"Find unusual revenue transactions"

**How it works:**
1. **Fetches revenue data** (up to 1000 records)
2. **Calculates statistics:**
   - Mean revenue
   - Standard deviation
   - Median revenue
3. **Defines thresholds:**
   ```
   upper_threshold = mean + (multiplier × std_dev)
   lower_threshold = mean - (multiplier × std_dev)
   ```
   Default multiplier: 2.0 (95.4% confidence)
4. **Classifies anomalies:**
   - **High anomalies:** revenue > upper_threshold
   - **Low anomalies:** revenue < lower_threshold (but > 0)
5. **Returns:**
   - Statistical summary
   - Top 10 high-value anomalies
   - Top 10 low-value anomalies
   - Z-scores for each anomaly

**Logic:**
```python
for transaction in data:
    z_score = (value - mean) / std_dev
    if abs(z_score) > threshold:
        anomaly_found.append({
            record, value, z_score,
            deviation_from_mean
        })
```

---

### 25. Detect Time Pattern Anomalies (Tool #25 in implementation)
**Tool Name:** `detect_time_pattern_anomalies`

**What it does:**
Identifies unusual time-based patterns: gaps in activity, unusual day-of-week patterns, irregular monthly trends.

**Example Use Case:**
"Find unusual patterns in transaction timing"

**How it works:**
1. **Day of Week Analysis:**
   ```sql
   SELECT EXTRACT(DOW FROM date), COUNT(*), SUM(value)
   FROM table
   GROUP BY day_of_week
   ```
   - Calculates mean and std dev across days
   - Flags days >1.5 std deviations from mean
   - Identifies unusually high/low activity days

2. **Monthly Pattern Analysis:**
   - Groups by month
   - Tracks trends over time
   - Detects seasonal variations

3. **Activity Gap Detection:**
   ```sql
   WITH date_series AS (
       SELECT generate_series(min_date, max_date, '1 day')
   )
   SELECT dates WHERE activity_count = 0
   ```
   - Finds days with zero activity
   - Returns up to 50 gaps

4. **Anomaly Types:**
   - Unusual day patterns (weekend vs weekday)
   - Activity gaps (system downtime?)
   - Monthly irregularities

**Logic:**
- Generate complete date series
- Left join with actual activity
- Identify gaps and unusual patterns
- Statistical analysis of distributions

---

### 26. Detect Customer Behavior Anomalies (Tool #26 in implementation)
**Tool Name:** `detect_customer_behavior_anomalies`

**What it does:**
Identifies unusual customer purchasing behaviors and transaction patterns (high-value customers, unusual frequency patterns).

**Example Use Case:**
"Find customers with unusual buying patterns"

**How it works:**
1. **Customer Aggregation:**
   ```sql
   SELECT customer_id,
       COUNT(*) as transaction_count,
       SUM(value) as total_value,
       AVG(value) as avg_value,
       MIN(value), MAX(value)
   FROM transactions
   GROUP BY customer_id
   ```

2. **Statistical Analysis:**
   - Mean customer lifetime value
   - Standard deviation
   - Thresholds (default 2.5 std devs)

3. **Anomaly Detection:**
   
   a. **High-Value Customers:**
   ```
   total_value > mean + (2.5 × std_dev)
   ```
   
   b. **Unusual Frequency Patterns:**
   - High frequency, low value: >10 transactions, <50% mean value
   - Low frequency, high value: <2 transactions, >150% mean value

4. **Returns:**
   - Top 10 high-value customers
   - Top 10 unusual frequency patterns
   - Statistical summary
   - Customer behavior insights

**Logic:**
```python
for customer in data:
    if total_value > upper_threshold:
        high_value_customers.append(customer)
    
    avg_per_trans = total_value / trans_count
    
    if (trans_count > 10 and total_value < mean * 0.5):
        unusual_frequency.append({
            customer,
            pattern: 'high_frequency_low_value'
        })
    
    elif (trans_count < 2 and total_value > mean * 1.5):
        unusual_frequency.append({
            customer,
            pattern: 'low_frequency_high_value'
        })
```

---

## 🎯 Tool Selection Strategy

### When to Use Which Tool:

1. **Starting Investigation:**
   - `get_database_schema` → Understand structure
   - `describe_table` → Focus on specific table
   - `get_table_sample_data` → See actual data

2. **Data Quality Checks:**
   - `analyze_data_quality` → Overall quality assessment
   - `get_column_statistics` → Deep dive into specific columns

3. **Finding Insights:**
   - `detect_data_anomalies` → Find outliers
   - `find_correlations` → Discover relationships
   - `detect_seasonal_patterns` → Identify cycles

4. **Deep Investigation:**
   - `generate_drill_down_queries` → Create follow-ups
   - `compare_time_periods` → Temporal comparison
   - Anomaly detection tools → Specific pattern analysis

5. **Visualization:**
   - `suggest_visualization` → Get recommendations
   - `generate_chart` → General charting
   - Specific chart tools → Type-specific charts

6. **Business Reporting:**
   - `get_key_business_metrics` → KPI dashboard
   - `generate_business_summary` → Executive report

7. **Query Optimization:**
   - `validate_sql_syntax` → Check before running
   - `explain_query_plan` → Understand performance
   - `optimize_query` → Get improvement suggestions

---

## 🔐 Safety Features

All tools include built-in safety:

1. **SQL Injection Prevention:**
   - Parameterized queries
   - Input validation
   - Pattern matching for dangerous operations

2. **Resource Protection:**
   - Automatic LIMIT clauses
   - Query timeouts
   - READ-ONLY operations only

3. **Error Handling:**
   - Graceful failures
   - Detailed error messages
   - Transaction rollback

4. **Performance Safeguards:**
   - Estimation before full scans
   - Limited result sets
   - Efficient query patterns

---

## 📝 Summary

The 22 tools provide comprehensive database investigation capabilities:

- **4 Discovery Tools:** Understand any database structure
- **4 SQL Tools:** Execute and optimize queries safely
- **4 Analysis Tools:** Statistical analysis and correlations
- **3 Investigation Tools:** Deep-dive and pattern detection
- **6 Visualization Tools:** Create charts and graphs
- **2 Business Tools:** KPI dashboards and reports
- **3 Anomaly Tools:** Specialized pattern detection

All tools are **schema-agnostic**, working with any PostgreSQL database through dynamic query generation and metadata inspection.

