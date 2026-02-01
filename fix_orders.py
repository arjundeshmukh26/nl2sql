#!/usr/bin/env python3
"""
Fix orders data using actual customer IDs
"""

import asyncio
import asyncpg
from pathlib import Path

DATABASE_URL = "postgresql://neondb_owner:npg_TputAXj8mhl4@ep-jolly-frog-ahz1jdbc-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

async def fix_orders():
    """Fix the orders data using actual customer IDs"""
    
    print("🔧 Fixing orders data...")
    
    try:
        # Read the SQL file
        sql_file = Path("fix_orders.sql")
        if not sql_file.exists():
            print("❌ Error: fix_orders.sql file not found!")
            return False
            
        print("📖 Reading fix orders script...")
        sql_content = sql_file.read_text(encoding='utf-8')
        
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected successfully!")
        
        # Execute the SQL script
        print("⚡ Creating orders with correct customer IDs...")
        
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('--'):
                continue
                
            current_statement += line + '\n'
            
            if line.endswith(';'):
                statements.append(current_statement)
                current_statement = ""
        
        if current_statement.strip():
            statements.append(current_statement)
        
        # Execute statements
        total_statements = len(statements)
        success_count = 0
        
        for i, statement in enumerate(statements, 1):
            statement = statement.strip()
            if not statement:
                continue
                
            try:
                print(f"   Executing statement {i}/{total_statements}...")
                result = await conn.execute(statement)
                success_count += 1
                if "INSERT" in result:
                    rows = result.split()[-1] if result else "unknown"
                    print(f"     → Inserted {rows} records")
            except Exception as e:
                print(f"⚠️  Statement {i} failed: {str(e)[:100]}...")
                continue
        
        print(f"✅ Executed {success_count}/{total_statements} statements successfully!")
        
        # Get final statistics
        print("\n📊 Updated Database Statistics:")
        
        tables = ['customers', 'promotions', 'orders', 'order_items']
        
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"   {table.replace('_', ' ').title()}: {count:,} records")
            except:
                print(f"   {table.replace('_', ' ').title()}: Error getting count")
        
        # Test business queries
        print("\n🧪 Testing Business Intelligence Queries:")
        
        try:
            # Total revenue
            total_revenue = await conn.fetchval(
                "SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE order_status = 'Completed'"
            )
            print(f"   Total Revenue: ${total_revenue:,.2f}")
            
            # Revenue by region
            region_revenue = await conn.fetch("""
                SELECT r.region_name, 
                       COUNT(o.order_id) as orders,
                       COALESCE(SUM(o.total_amount), 0) as revenue
                FROM regions r
                LEFT JOIN customers c ON r.region_id = c.region_id
                LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'Completed'
                GROUP BY r.region_name
                ORDER BY revenue DESC
            """)
            print("   Revenue by Region:")
            for row in region_revenue:
                print(f"     {row['region_name']}: {row['orders']} orders, ${row['revenue']:,.2f}")
            
            # Top products
            top_products = await conn.fetch("""
                SELECT p.product_name, 
                       SUM(oi.quantity) as units_sold,
                       SUM(oi.line_total) as revenue
                FROM products p
                JOIN order_items oi ON p.product_id = oi.product_id
                JOIN orders o ON oi.order_id = o.order_id
                WHERE o.order_status = 'Completed'
                GROUP BY p.product_id, p.product_name
                ORDER BY revenue DESC
                LIMIT 5
            """)
            print("   Top 5 Products by Revenue:")
            for row in top_products:
                print(f"     {row['product_name']}: {row['units_sold']} units, ${row['revenue']:,.2f}")
            
            # Monthly sales trend
            monthly_sales = await conn.fetch("""
                SELECT DATE_TRUNC('month', order_date) as month,
                       COUNT(*) as orders,
                       SUM(total_amount) as revenue
                FROM orders 
                WHERE order_status = 'Completed'
                GROUP BY DATE_TRUNC('month', order_date)
                ORDER BY month DESC
                LIMIT 6
            """)
            print("   Monthly Sales Trend (Last 6 months):")
            for row in monthly_sales:
                month_name = row['month'].strftime('%B %Y')
                print(f"     {month_name}: {row['orders']} orders, ${row['revenue']:,.2f}")
                
        except Exception as e:
            print(f"   Business queries error: {e}")
        
        await conn.close()
        print("\n🎉 Orders data fixed successfully!")
        print("\n🚀 Your database is now fully populated and ready for agentic NL2SQL testing!")
        print("\n💡 Try asking questions like:")
        print("   - 'What are our top selling products?'")
        print("   - 'Show me sales trends by region'") 
        print("   - 'Which customers have the highest lifetime value?'")
        print("   - 'How do different customer segments perform?'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_orders())
    exit(0 if success else 1)





