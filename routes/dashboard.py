from flask import Blueprint, render_template, session
from auth import login_required, get_current_user
from models import Product, Sale, Purchase, Customer, Inventory, db
from sqlalchemy import func, text
from datetime import datetime, timedelta
from app import cache

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    user = get_current_user()
    
    # Cache key based on user and current hour for fresh data
    cache_key = f"dashboard_stats_{user.id}_{datetime.now().hour}"
    
    @cache.memoize(timeout=300)  # 5 minutes cache
    def get_dashboard_stats():
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        # Basic counts
        total_products = Product.query.filter_by(is_active=True).count()
        total_customers = Customer.query.filter_by(is_active=True, type='client').count()
        total_suppliers = Customer.query.filter_by(is_active=True, type='supplier').count()
        
        # Sales stats
        today_sales = db.session.query(func.sum(Sale.total)).filter(
            func.date(Sale.created_at) == today
        ).scalar() or 0
        
        month_sales = db.session.query(func.sum(Sale.total)).filter(
            Sale.created_at >= month_start
        ).scalar() or 0
        
        # Low stock products
        low_stock_query = text("""
            SELECT p.name, p.sku, i.quantity, i.min_stock, w.name as warehouse
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            JOIN warehouses w ON i.warehouse_id = w.id
            WHERE i.quantity <= i.min_stock AND i.min_stock > 0
            ORDER BY (i.quantity / NULLIF(i.min_stock, 0)) ASC
            LIMIT 10
        """)
        
        low_stock = db.session.execute(low_stock_query).fetchall()
        
        # Recent sales
        recent_sales = Sale.query.join(Customer).order_by(Sale.created_at.desc()).limit(5).all()
        
        # Top selling products this month
        top_products_query = text("""
            SELECT p.name, p.sku, SUM(sd.quantity) as total_sold, SUM(sd.total) as total_revenue
            FROM products p
            JOIN sale_details sd ON p.id = sd.product_id
            JOIN sales s ON sd.sale_id = s.id
            WHERE s.created_at >= :month_start
            GROUP BY p.id, p.name, p.sku
            ORDER BY total_sold DESC
            LIMIT 10
        """)
        
        top_products = db.session.execute(top_products_query, {"month_start": month_start}).fetchall()
        
        return {
            'total_products': total_products,
            'total_customers': total_customers,
            'total_suppliers': total_suppliers,
            'today_sales': today_sales,
            'month_sales': month_sales,
            'low_stock': low_stock,
            'recent_sales': recent_sales,
            'top_products': top_products
        }
    
    stats = get_dashboard_stats()
    
    return render_template('dashboard.html', 
                         user=user,
                         **stats)
