#!/usr/bin/env python3
"""
Database initialization script for the agentic NL2SQL system.
Executes the comprehensive sales database setup.
"""

import asyncpg
import asyncio
import sys
from pathlib import Path

# Database connection string
DATABASE_URL = "postgresql://neondb_owner:npg_TputAXj8mhl4@ep-jolly-frog-ahz1jdbc-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

async def init_database():
    """Initialize the database with sample sales data"""
    
    print("🚀 Starting database initialization...")
    
    try:
        # Read the SQL file
        sql_file = Path("database_init.sql")
        if not sql_file.exists():
            print("❌ Error: database_init.sql file not found!")
            return False
            
        print("📖 Reading SQL initialization script...")
        sql_content = sql_file.read_text(encoding='utf-8')
        
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected successfully!")
        
        # Execute the SQL script
        print("⚡ Executing database initialization script...")
        print("   This may take a few minutes due to the large amount of sample data...")
        
        # Split the SQL content into individual statements
        # We need to handle this carefully due to the DO blocks
        statements = []
        current_statement = ""
        in_do_block = False
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('--'):
                continue
                
            # Check for DO block start
            if line.upper().startswith('DO $$'):
                in_do_block = True
                current_statement += line + '\n'
                continue
                
            # Check for DO block end
            if in_do_block and line == '$$;':
                current_statement += line
                statements.append(current_statement)
                current_statement = ""
                in_do_block = False
                continue
                
            # Add line to current statement
            current_statement += line + '\n'
            
            # Check for statement end (semicolon) - but not in DO blocks
            if not in_do_block and line.endswith(';'):
                statements.append(current_statement)
                current_statement = ""
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement)
        
        # Execute statements one by one
        total_statements = len(statements)
        for i, statement in enumerate(statements, 1):
            statement = statement.strip()
            if not statement:
                continue
                
            try:
                print(f"   Executing statement {i}/{total_statements}...")
                await conn.execute(statement)
            except Exception as e:
                print(f"⚠️  Warning: Statement {i} failed: {str(e)}")
                # Continue with other statements
                continue
        
        print("✅ Database initialization completed successfully!")
        
        # Get final statistics
        print("\n📊 Database Statistics:")
        
        tables = [
            'regions', 'customer_segments', 'categories', 'suppliers', 
            'products', 'stores', 'sales_reps', 'customers', 
            'promotions', 'orders', 'order_items'
        ]
        
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"   {table.replace('_', ' ').title()}: {count:,} records")
            except Exception as e:
                print(f"   {table.replace('_', ' ').title()}: Error getting count")
        
        # Test some sample queries
        print("\n🧪 Testing sample business queries:")
        
        # Total revenue
        try:
            total_revenue = await conn.fetchval(
                "SELECT SUM(total_amount) FROM orders WHERE order_status = 'Completed'"
            )
            print(f"   Total Revenue: ${total_revenue:,.2f}")
        except Exception as e:
            print(f"   Total Revenue: Error - {e}")
        
        # Orders by region
        try:
            region_stats = await conn.fetch("""
                SELECT r.region_name, COUNT(o.order_id) as order_count, SUM(o.total_amount) as revenue
                FROM regions r
                JOIN customers c ON r.region_id = c.region_id
                JOIN orders o ON c.customer_id = o.customer_id
                WHERE o.order_status = 'Completed'
                GROUP BY r.region_name
                ORDER BY revenue DESC
                LIMIT 3
            """)
            print("   Top 3 Regions by Revenue:")
            for row in region_stats:
                print(f"     {row['region_name']}: {row['order_count']} orders, ${row['revenue']:,.2f}")
        except Exception as e:
            print(f"   Region stats: Error - {e}")
        
        await conn.close()
        print("\n🎉 Database is ready for your agentic NL2SQL system!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)





