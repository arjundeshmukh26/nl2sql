# 🔍 Anomaly Detection System - User Guide

## ✅ What Was Fixed

### 1. **Schema-Agnostic Design** 
❌ **Before**: Tools were hardcoded to work only with specific tables (`customers`, `sales`, `products`)  
✅ **After**: Tools now accept table names and column names as parameters, making them work with **any database schema**

### 2. **No More Missing Table Errors**
❌ **Before**: `relation "customers" does not exist` errors  
✅ **After**: Tools query only the tables you specify

### 3. **DATE Type Compatibility**
❌ **Before**: `unit "hour" not supported for type date` errors  
✅ **After**: Proper casting to `timestamp` for time-based analysis

---

## 🛠️ How to Use Anomaly Detection Tools

### **1. Detect Revenue Anomalies**

Finds unusual high or low values in any numeric column.

**Required Parameters:**
- `table_name`: The table to analyze (e.g., "sales", "orders")
- `revenue_column`: The numeric column to analyze (e.g., "revenue", "amount", "total")
- `threshold_multiplier`: (optional, default: 2.0) How many standard deviations define an anomaly

**Example Query:**
```
"Find revenue anomalies in the sales table"
```

**What It Does:**
- Calculates mean, median, and standard deviation
- Identifies values that are 2+ standard deviations from the mean
- Returns high-value and low-value outliers
- Shows statistical significance of each anomaly

---

### **2. Detect Time Pattern Anomalies**

Finds unusual patterns in time-series data like gaps, unusual day-of-week patterns, or irregular monthly trends.

**Required Parameters:**
- `table_name`: The table to analyze
- `date_column`: The date/timestamp column
- `value_column`: (optional) Column to aggregate (uses count if not specified)

**Example Query:**
```
"Find unusual time patterns in our sales data"
```

**What It Does:**
- Analyzes day-of-week patterns (e.g., unusually high Monday sales)
- Detects gaps in activity (days with zero transactions)
- Identifies monthly trends and deviations
- Flags unusual temporal patterns

---

### **3. Detect Customer Behavior Anomalies**

Finds unusual customer purchasing patterns.

**Required Parameters:**
- `transaction_table`: Table containing transactions
- `customer_id_column`: Column identifying customers
- `value_column`: Transaction value column
- `threshold_multiplier`: (optional, default: 2.5)

**Example Query:**
```
"Find unusual customer behaviors in sales"
```

**What It Does:**
- Identifies customers with abnormally high spending
- Detects unusual transaction frequencies
- Flags suspicious patterns (e.g., many low-value transactions)
- Shows customer outliers with statistical significance

---

## 📊 Sample Queries

### For Your Database:

Since your database has `sales`, `products`, and `markets` tables:

1. **"Find anomalies in sales revenue"**
   - Tool will use: `table_name="sales"`, `revenue_column="revenue"`

2. **"Detect unusual time patterns in sales"**
   - Tool will use: `table_name="sales"`, `date_column="sale_date"`

3. **"Find unusual purchasing patterns by customer"**
   - Tool will use: `transaction_table="sales"`, `customer_id_column="customer_id"`, `value_column="revenue"`
   - ⚠️ Note: This requires a `customer_id` column in your sales table

---

## 🎯 How the Agent Uses These Tools

When you ask: **"Find anomalies and unusual patterns in our data"**

The agent will:

1. ✅ **get_database_schema** - Discover available tables and columns
2. ✅ **detect_revenue_anomalies** - Analyze revenue outliers
   - Parameters: `table_name="sales"`, `revenue_column="revenue"`
3. ✅ **detect_time_pattern_anomalies** - Find temporal anomalies
   - Parameters: `table_name="sales"`, `date_column="sale_date"`, `value_column="revenue"`
4. ✅ **detect_customer_behavior_anomalies** - Find customer outliers (if customer_id exists)
   - Parameters: `transaction_table="sales"`, `customer_id_column="customer_id"`, `value_column="revenue"`
5. ✅ **Visualizations** - Generate charts showing anomalies

---

## 🔧 Technical Details

### What Makes It Schema-Agnostic?

**Before:**
```python
query = "SELECT * FROM sales JOIN customers ON..."  # Hardcoded!
```

**After:**
```python
query = f"SELECT * FROM {table_name} WHERE {revenue_column} > 0"  # Dynamic!
```

### Statistical Methods Used:

- **Mean & Standard Deviation**: For outlier detection
- **Threshold-based**: Values beyond N standard deviations are anomalies
- **Time-series Analysis**: Day-of-week, monthly, and gap detection
- **Frequency Analysis**: Transaction count vs. value patterns

---

## 🚀 Benefits

1. **Works with ANY database schema**
2. **No hardcoded table names**
3. **Flexible column mapping**
4. **Statistical rigor** (configurable thresholds)
5. **Clear anomaly categorization**
6. **Detailed explanations** (deviation from mean, std deviations)

---

## 📌 Quick Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `detect_revenue_anomalies` | Find outliers in numeric data | `table_name`, `revenue_column` |
| `detect_time_pattern_anomalies` | Find temporal patterns | `table_name`, `date_column` |
| `detect_customer_behavior_anomalies` | Find customer outliers | `transaction_table`, `customer_id_column` |

---

## 💡 Pro Tips

1. **Adjust sensitivity**: Use `threshold_multiplier` to control how strict the anomaly detection is
   - Lower values (1.5) = More sensitive, finds more anomalies
   - Higher values (3.0) = Less sensitive, finds only extreme outliers

2. **Combine with visualizations**: The agent will generate charts showing anomalies visually

3. **Check multiple dimensions**: Anomalies might exist in revenue, time patterns, or customer behavior

4. **Use for data quality**: Anomaly detection can reveal data entry errors or system issues

---

## 🎯 Next Steps

1. **Test with your query**: `"Find anomalies and unusual patterns in our data"`
2. **Check the results**: Look for statistical summaries and specific anomalous records
3. **Investigate findings**: Drill down into flagged anomalies
4. **Adjust thresholds**: If too many/few anomalies, adjust `threshold_multiplier`

---

**Need Help?** The tools are now fully dynamic and work with any schema. Just provide table and column names!



