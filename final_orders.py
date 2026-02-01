#!/usr/bin/env python3
"""
Final orders data creation - clears existing and creates fresh data
"""

import asyncio
import asyncpg
import random
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://neondb_owner:npg_TputAXj8mhl4@ep-jolly-frog-ahz1jdbc-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

async def create_final_orders():
    """Create fresh orders data"""
    
    print("🔧 Creating fresh orders data...")
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected successfully!")
        
        # Clear existing orders first
        print("🧹 Clearing existing orders...")
        await conn.execute("TRUNCATE TABLE order_items, orders CASCADE")
        print("   Cleared existing orders and items")
        
        # Get existing data
        print("📊 Getting existing data...")
        customers = await conn.fetch("SELECT customer_id, region_id, segment_id FROM customers ORDER BY customer_id")
        sales_reps = await conn.fetch("SELECT rep_id FROM sales_reps ORDER BY rep_id")
        stores = await conn.fetch("SELECT store_id FROM stores ORDER BY store_id")
        promotions = await conn.fetch("SELECT promotion_id FROM promotions ORDER BY promotion_id")
        products = await conn.fetch("SELECT product_id, unit_price, cost_price FROM products ORDER BY product_id")
        
        print(f"   Found {len(customers)} customers, {len(sales_reps)} reps, {len(stores)} stores, {len(products)} products")
        
        if not customers or not products:
            print("❌ No customers or products found! Please run the initial data setup first.")
            return False
        
        # Create orders in smaller batches to avoid connection timeouts
        print("⚡ Creating orders in batches...")
        orders_created = 0
        items_created = 0
        
        # Create 300 orders (smaller number to avoid timeouts)
        batch_size = 50
        total_orders = 300
        
        for batch_start in range(0, total_orders, batch_size):
            batch_end = min(batch_start + batch_size, total_orders)
            print(f"   Creating orders {batch_start + 1} to {batch_end}...")
            
            for i in range(batch_start, batch_end):
                try:
                    # Random customer
                    customer = random.choice(customers)
                    customer_id = customer['customer_id']
                    
                    # Random sales rep and store
                    rep_id = random.choice(sales_reps)['rep_id']
                    store_id = random.choice(stores)['store_id']
                    
                    # Random promotion (30% chance)
                    promotion_id = random.choice(promotions)['promotion_id'] if random.random() < 0.3 else None
                    
                    # Random date in last year
                    days_ago = random.randint(1, 365)
                    order_date = datetime.now().date() - timedelta(days=days_ago)
                    ship_date = order_date + timedelta(days=random.randint(1, 5))
                    delivery_date = ship_date + timedelta(days=random.randint(1, 7))
                    
                    # Order status
                    if days_ago > 30:
                        order_status = 'Completed'
                    else:
                        order_status = random.choice(['Completed', 'Completed', 'Completed', 'Shipped', 'Processing'])
                    
                    # Payment method
                    payment_method = random.choice(['Credit Card', 'Credit Card', 'Debit Card', 'PayPal'])
                    
                    # Order number with timestamp to ensure uniqueness
                    order_number = f'ORD-{datetime.now().strftime("%Y%m%d")}-{i+1:06d}'
                    
                    # Create 1-3 order items first to calculate totals
                    num_items = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
                    selected_products = random.sample(products, min(num_items, len(products)))
                    
                    order_subtotal = 0
                    order_profit = 0
                    order_items_data = []
                    
                    for product in selected_products:
                        product_id = product['product_id']
                        unit_price = float(product['unit_price'])
                        unit_cost = float(product['cost_price'])
                        
                        quantity = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
                        discount_pct = 0 if random.random() < 0.85 else round(random.uniform(5, 15), 2)
                        
                        line_total = round(quantity * unit_price * (1 - discount_pct/100), 2)
                        line_profit = round(quantity * (unit_price - unit_cost) * (1 - discount_pct/100), 2)
                        
                        order_subtotal += line_total
                        order_profit += line_profit
                        
                        order_items_data.append({
                            'product_id': product_id,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'unit_cost': unit_cost,
                            'discount_pct': discount_pct,
                            'line_total': line_total,
                            'line_profit': line_profit
                        })
                    
                    # Apply promotion discount if applicable
                    discount_amount = 0
                    if promotion_id:
                        promo = await conn.fetchrow("SELECT discount_percentage FROM promotions WHERE promotion_id = $1", promotion_id)
                        if promo and promo['discount_percentage']:
                            discount_amount = round(order_subtotal * float(promo['discount_percentage']) / 100, 2)
                    
                    # Calculate final totals
                    tax_amount = round(order_subtotal * 0.0875, 2)  # 8.75% tax
                    shipping_cost = 0 if order_subtotal > 100 else round(random.uniform(5, 15), 2)
                    total_amount = round(order_subtotal + tax_amount + shipping_cost - discount_amount, 2)
                    
                    # Insert order
                    order_id = await conn.fetchval("""
                        INSERT INTO orders (order_number, customer_id, sales_rep_id, store_id, promotion_id,
                                          order_date, ship_date, delivery_date, order_status, payment_method,
                                          subtotal, tax_amount, shipping_cost, discount_amount, total_amount, profit_margin)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                        RETURNING order_id
                    """, order_number, customer_id, rep_id, store_id, promotion_id,
                        order_date, ship_date, delivery_date, order_status, payment_method,
                        order_subtotal, tax_amount, shipping_cost, discount_amount, total_amount, order_profit)
                    
                    orders_created += 1
                    
                    # Insert order items
                    for item_data in order_items_data:
                        await conn.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost,
                                                   discount_percentage, line_total, line_profit)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """, order_id, item_data['product_id'], item_data['quantity'], 
                            item_data['unit_price'], item_data['unit_cost'], item_data['discount_pct'],
                            item_data['line_total'], item_data['line_profit'])
                        
                        items_created += 1
                
                except Exception as e:
                    print(f"   ⚠️ Failed to create order {i+1}: {str(e)[:50]}...")
                    continue
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        print(f"✅ Created {orders_created} orders with {items_created} items!")
        
        # Update customer totals
        print("📊 Updating customer totals...")
        await conn.execute("""
            UPDATE customers SET 
                total_spent = COALESCE((
                    SELECT SUM(o.total_amount) 
                    FROM orders o 
                    WHERE o.customer_id = customers.customer_id 
                    AND o.order_status = 'Completed'
                ), 0),
                last_purchase_date = (
                    SELECT MAX(o.order_date) 
                    FROM orders o 
                    WHERE o.customer_id = customers.customer_id
                ),
                loyalty_points = COALESCE((
                    SELECT SUM(o.total_amount)::INTEGER / 10 
                    FROM orders o 
                    WHERE o.customer_id = customers.customer_id 
                    AND o.order_status = 'Completed'
                ), 0)
        """)
        
        # Get final statistics
        print("\n📊 Final Database Statistics:")
        
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
            print(f"   💰 Total Revenue: ${total_revenue:,.2f}")
            
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
                LIMIT 5
            """)
            print("   🌍 Top Regions by Revenue:")
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
                LIMIT 3
            """)
            print("   🏆 Top 3 Products by Revenue:")
            for row in top_products:
                print(f"     {row['product_name']}: {row['units_sold']} units, ${row['revenue']:,.2f}")
                
        except Exception as e:
            print(f"   ⚠️ Business queries error: {e}")
        
        await conn.close()
        print("\n🎉 Database is now fully populated and ready!")
        print("\n🚀 Perfect for testing your agentic NL2SQL system!")
        print("\n💡 Sample questions you can now ask:")
        print("   - 'What are our top selling products by revenue?'")
        print("   - 'Show me sales performance by region'") 
        print("   - 'Which customer segment has the highest average order value?'")
        print("   - 'What are the monthly sales trends?'")
        print("   - 'Which products have the best profit margins?'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(create_final_orders())
    exit(0 if success else 1)
