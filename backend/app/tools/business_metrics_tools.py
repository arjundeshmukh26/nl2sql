"""
Business metrics tools for generating key performance indicators
"""

from typing import List, Dict, Any, Optional
from .base_tool import BaseTool, ToolParameter, ToolResult


class GetKeyBusinessMetricsTool(BaseTool):
    """Get essential business metrics for sales performance analysis"""
    
    @property
    def name(self) -> str:
        return "get_key_business_metrics"
    
    @property
    def description(self) -> str:
        return "Execute key business metrics queries to get total revenue, sales count, average order value, and other essential KPIs."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # No parameters needed
    
    async def execute(self) -> ToolResult:
        """Execute key business metrics queries"""
        try:
            conn = await self.db_manager.get_connection()
            
            metrics = {}
            
            # 1. Total Revenue and Sales Count
            revenue_query = """
                SELECT 
                    COUNT(*) as total_sales,
                    SUM(revenue) as total_revenue,
                    AVG(revenue) as avg_order_value,
                    SUM(quantity) as total_quantity
                FROM sales
            """
            revenue_result = await conn.fetchrow(revenue_query)
            if revenue_result:
                metrics['overview'] = dict(revenue_result)
            
            # 2. Top 5 Products by Revenue
            top_products_query = """
                SELECT 
                    p.product_name,
                    SUM(s.revenue) as total_revenue,
                    COUNT(*) as sales_count
                FROM sales s 
                JOIN products p ON s.product_id = p.id 
                GROUP BY p.product_name 
                ORDER BY total_revenue DESC 
                LIMIT 5
            """
            top_products = await conn.fetch(top_products_query)
            metrics['top_products'] = [dict(row) for row in top_products]
            
            # 3. Revenue by Market
            market_query = """
                SELECT 
                    m.market_name,
                    SUM(s.revenue) as market_revenue,
                    COUNT(*) as sales_count
                FROM sales s 
                JOIN markets m ON s.market_id = m.id 
                GROUP BY m.market_name 
                ORDER BY market_revenue DESC
            """
            markets = await conn.fetch(market_query)
            metrics['markets'] = [dict(row) for row in markets]
            
            # 4. Monthly Revenue Trends (last 12 months)
            monthly_query = """
                SELECT 
                    DATE_TRUNC('month', sale_date) as month,
                    SUM(revenue) as monthly_revenue,
                    COUNT(*) as monthly_sales
                FROM sales 
                WHERE sale_date >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY month 
                ORDER BY month DESC
                LIMIT 12
            """
            monthly = await conn.fetch(monthly_query)
            metrics['monthly_trends'] = [dict(row) for row in monthly]
            
            # 5. Performance Summary
            summary = {
                'total_revenue': metrics['overview']['total_revenue'] if metrics.get('overview') else 0,
                'total_sales': metrics['overview']['total_sales'] if metrics.get('overview') else 0,
                'avg_order_value': metrics['overview']['avg_order_value'] if metrics.get('overview') else 0,
                'top_product': metrics['top_products'][0]['product_name'] if metrics.get('top_products') else 'N/A',
                'top_market': metrics['markets'][0]['market_name'] if metrics.get('markets') else 'N/A',
                'metrics_generated': True
            }
            
            return ToolResult(
                success=True,
                data={
                    'summary': summary,
                    'detailed_metrics': metrics,
                    'queries_executed': 4,
                    'timestamp': 'now'
                },
                execution_time_ms=1000,
                metadata={
                    'metric_categories': ['overview', 'top_products', 'markets', 'monthly_trends'],
                    'total_data_points': sum([
                        1,  # overview
                        len(metrics.get('top_products', [])),
                        len(metrics.get('markets', [])),
                        len(metrics.get('monthly_trends', []))
                    ])
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting key business metrics: {str(e)}",
                execution_time_ms=0
            )


class GenerateBusinessSummaryTool(BaseTool):
    """Generate a comprehensive business summary with metrics"""
    
    @property
    def name(self) -> str:
        return "generate_business_summary"
    
    @property
    def description(self) -> str:
        return "Generate a comprehensive business performance summary with key metrics, trends, and insights."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # No parameters needed
    
    async def execute(self) -> ToolResult:
        """Generate business summary with metrics"""
        try:
            # First get the key metrics
            metrics_tool = GetKeyBusinessMetricsTool(self.db_manager)
            metrics_result = await metrics_tool.execute()
            
            if not metrics_result.success:
                return metrics_result
            
            metrics = metrics_result.data['detailed_metrics']
            summary = metrics_result.data['summary']
            
            # Generate insights based on the metrics
            insights = []
            
            # Revenue insights
            if summary['total_revenue'] > 0:
                insights.append(f"💰 Total Revenue: ${summary['total_revenue']:,.2f}")
                insights.append(f"📊 Total Sales: {summary['total_sales']:,} transactions")
                insights.append(f"💳 Average Order Value: ${summary['avg_order_value']:.2f}")
            
            # Product insights
            if metrics.get('top_products'):
                top_product = metrics['top_products'][0]
                insights.append(f"🏆 Top Product: {top_product['product_name']} (${top_product['total_revenue']:,.2f})")
                
                # Calculate top product percentage
                if summary['total_revenue'] > 0:
                    top_product_pct = (top_product['total_revenue'] / summary['total_revenue']) * 100
                    insights.append(f"📈 Top Product Share: {top_product_pct:.1f}% of total revenue")
            
            # Market insights
            if metrics.get('markets'):
                top_market = metrics['markets'][0]
                insights.append(f"🌍 Top Market: {top_market['market_name']} (${top_market['market_revenue']:,.2f})")
            
            # Trend insights
            if metrics.get('monthly_trends') and len(metrics['monthly_trends']) >= 2:
                recent_month = metrics['monthly_trends'][0]
                previous_month = metrics['monthly_trends'][1]
                
                if previous_month['monthly_revenue'] > 0:
                    growth = ((recent_month['monthly_revenue'] - previous_month['monthly_revenue']) / previous_month['monthly_revenue']) * 100
                    trend_direction = "📈 Growing" if growth > 0 else "📉 Declining"
                    insights.append(f"{trend_direction}: {abs(growth):.1f}% month-over-month")
            
            business_summary = {
                'executive_summary': {
                    'total_revenue': summary['total_revenue'],
                    'total_sales': summary['total_sales'],
                    'avg_order_value': summary['avg_order_value'],
                    'performance_status': 'Active' if summary['total_sales'] > 0 else 'No Data'
                },
                'key_insights': insights,
                'top_performers': {
                    'product': summary['top_product'],
                    'market': summary['top_market']
                },
                'detailed_breakdown': metrics,
                'recommendations': [
                    f"Focus on promoting {summary['top_product']} as it's the top performer",
                    f"Expand operations in {summary['top_market']} market",
                    "Analyze monthly trends to identify seasonal patterns",
                    "Consider strategies to increase average order value"
                ]
            }
            
            return ToolResult(
                success=True,
                data=business_summary,
                execution_time_ms=500,
                metadata={
                    'insights_count': len(insights),
                    'recommendations_count': 4,
                    'data_freshness': 'real-time'
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error generating business summary: {str(e)}",
                execution_time_ms=0
            )





