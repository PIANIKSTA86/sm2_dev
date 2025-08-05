from flask import Blueprint, render_template, request, jsonify, make_response
from auth import login_required, get_current_user
from models import Sale, Purchase, Product, Customer, Inventory, SaleDetail, PurchaseDetail, db
from sqlalchemy import func, text, extract
from datetime import datetime, timedelta
import json
from utils.pagination import paginate_query

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/sales_report')
@login_required
def sales_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    customer_id = request.args.get('customer_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    report_type = request.args.get('type', 'summary')
    
    # Default date range (last 30 days)
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    base_query = Sale.query.filter(
        Sale.created_at >= datetime.strptime(start_date, '%Y-%m-%d'),
        Sale.created_at <= datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    )
    
    if customer_id:
        base_query = base_query.filter_by(customer_id=customer_id)
    
    if warehouse_id:
        base_query = base_query.filter_by(warehouse_id=warehouse_id)
    
    if report_type == 'detailed':
        sales, pagination = paginate_query(base_query.order_by(Sale.created_at.desc()))
        
        return render_template('reports/sales_detailed.html',
                             sales=sales,
                             pagination=pagination,
                             start_date=start_date,
                             end_date=end_date,
                             customer_id=customer_id,
                             warehouse_id=warehouse_id)
    
    # Summary report
    summary = db.session.query(
        func.count(Sale.id).label('total_sales'),
        func.sum(Sale.subtotal).label('total_subtotal'),
        func.sum(Sale.tax_amount).label('total_tax'),
        func.sum(Sale.discount_amount).label('total_discount'),
        func.sum(Sale.total).label('total_amount')
    ).filter(
        Sale.created_at >= datetime.strptime(start_date, '%Y-%m-%d'),
        Sale.created_at <= datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    )
    
    if customer_id:
        summary = summary.filter_by(customer_id=customer_id)
    
    if warehouse_id:
        summary = summary.filter_by(warehouse_id=warehouse_id)
    
    summary_data = summary.first()
    
    # Daily sales chart data
    daily_sales_query = text("""
        SELECT DATE(created_at) as sale_date, 
               COUNT(*) as sales_count,
               SUM(total) as daily_total
        FROM sales 
        WHERE created_at >= :start_date AND created_at <= :end_date
        GROUP BY DATE(created_at)
        ORDER BY sale_date
    """)
    
    daily_sales = db.session.execute(daily_sales_query, {
        "start_date": start_date,
        "end_date": end_date + ' 23:59:59'
    }).fetchall()
    
    # Top selling products
    top_products_query = text("""
        SELECT p.name, p.sku, SUM(sd.quantity) as total_sold, SUM(sd.total) as total_revenue
        FROM products p
        JOIN sale_details sd ON p.id = sd.product_id
        JOIN sales s ON sd.sale_id = s.id
        WHERE s.created_at >= :start_date AND s.created_at <= :end_date
        GROUP BY p.id, p.name, p.sku
        ORDER BY total_sold DESC
        LIMIT 10
    """)
    
    top_products = db.session.execute(top_products_query, {
        "start_date": start_date,
        "end_date": end_date + ' 23:59:59'
    }).fetchall()
    
    from models import Customer, Warehouse
    customers = Customer.query.filter_by(type='client', is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    return render_template('reports/sales_summary.html',
                         summary=summary_data,
                         daily_sales=daily_sales,
                         top_products=top_products,
                         customers=customers,
                         warehouses=warehouses,
                         start_date=start_date,
                         end_date=end_date,
                         customer_id=customer_id,
                         warehouse_id=warehouse_id)

@reports_bp.route('/inventory_report')
@login_required
def inventory_report():
    warehouse_id = request.args.get('warehouse_id', type=int)
    category_id = request.args.get('category_id', type=int)
    show_zero = request.args.get('show_zero', type=bool)
    
    # Build inventory query
    query = text("""
        SELECT p.id, p.sku, p.name, p.cost, p.price1, 
               c.name as category_name, b.name as brand_name,
               w.name as warehouse_name,
               i.quantity, i.min_stock, i.max_stock,
               (i.quantity * p.cost) as inventory_value
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        JOIN inventory i ON p.id = i.product_id
        JOIN warehouses w ON i.warehouse_id = w.id
        WHERE p.is_active = true
        AND (:warehouse_id IS NULL OR i.warehouse_id = :warehouse_id)
        AND (:category_id IS NULL OR p.category_id = :category_id)
        AND (:show_zero OR i.quantity > 0)
        ORDER BY p.name
    """)
    
    inventory_data = db.session.execute(query, {
        "warehouse_id": warehouse_id,
        "category_id": category_id,
        "show_zero": show_zero
    }).fetchall()
    
    # Calculate totals
    total_value = sum(float(row.inventory_value or 0) for row in inventory_data)
    total_items = len(inventory_data)
    
    from models import Category, Warehouse
    categories = Category.query.filter_by(is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    return render_template('reports/inventory.html',
                         inventory_data=inventory_data,
                         total_value=total_value,
                         total_items=total_items,
                         categories=categories,
                         warehouses=warehouses,
                         warehouse_id=warehouse_id,
                         category_id=category_id,
                         show_zero=show_zero)

@reports_bp.route('/customer_report')
@login_required
def customer_report():
    customer_type = request.args.get('type', 'client')
    
    # Customer summary
    customer_stats_query = text("""
        SELECT c.id, c.name, c.email, c.phone,
               COUNT(s.id) as total_orders,
               COALESCE(SUM(s.total), 0) as total_spent,
               MAX(s.created_at) as last_order_date
        FROM customers c
        LEFT JOIN sales s ON c.id = s.customer_id
        WHERE c.type = :customer_type AND c.is_active = true
        GROUP BY c.id, c.name, c.email, c.phone
        ORDER BY total_spent DESC
    """)
    
    customer_stats = db.session.execute(customer_stats_query, {
        "customer_type": customer_type
    }).fetchall()
    
    return render_template('reports/customers.html',
                         customer_stats=customer_stats,
                         customer_type=customer_type)

@reports_bp.route('/profit_report')
@login_required
def profit_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Profit analysis by product
    profit_query = text("""
        SELECT p.name, p.sku,
               SUM(sd.quantity) as total_sold,
               AVG(p.cost) as avg_cost,
               AVG(sd.unit_price) as avg_sell_price,
               SUM(sd.total) as total_revenue,
               SUM(sd.quantity * p.cost) as total_cost,
               (SUM(sd.total) - SUM(sd.quantity * p.cost)) as gross_profit,
               CASE 
                   WHEN SUM(sd.total) > 0 THEN 
                       ((SUM(sd.total) - SUM(sd.quantity * p.cost)) / SUM(sd.total)) * 100
                   ELSE 0 
               END as profit_margin
        FROM products p
        JOIN sale_details sd ON p.id = sd.product_id
        JOIN sales s ON sd.sale_id = s.id
        WHERE s.created_at >= :start_date AND s.created_at <= :end_date
        GROUP BY p.id, p.name, p.sku
        HAVING SUM(sd.quantity) > 0
        ORDER BY gross_profit DESC
    """)
    
    profit_data = db.session.execute(profit_query, {
        "start_date": start_date,
        "end_date": end_date + ' 23:59:59'
    }).fetchall()
    
    # Overall profit summary
    total_revenue = sum(float(row.total_revenue) for row in profit_data)
    total_cost = sum(float(row.total_cost) for row in profit_data)
    total_profit = total_revenue - total_cost
    overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return render_template('reports/profit.html',
                         profit_data=profit_data,
                         total_revenue=total_revenue,
                         total_cost=total_cost,
                         total_profit=total_profit,
                         overall_margin=overall_margin,
                         start_date=start_date,
                         end_date=end_date)

@reports_bp.route('/export/<report_type>')
@login_required
def export_report(report_type):
    """Export reports to CSV"""
    import csv
    import io
    
    output = io.StringIO()
    
    if report_type == 'inventory':
        # Export inventory report
        warehouse_id = request.args.get('warehouse_id', type=int)
        
        query = text("""
            SELECT p.sku, p.name, p.cost, p.price1, 
                   c.name as category, b.name as brand,
                   w.name as warehouse, i.quantity, i.min_stock, i.max_stock
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            JOIN inventory i ON p.id = i.product_id
            JOIN warehouses w ON i.warehouse_id = w.id
            WHERE p.is_active = true
            AND (:warehouse_id IS NULL OR i.warehouse_id = :warehouse_id)
            ORDER BY p.name
        """)
        
        data = db.session.execute(query, {"warehouse_id": warehouse_id}).fetchall()
        
        writer = csv.writer(output)
        writer.writerow(['SKU', 'Nombre', 'Costo', 'Precio', 'Categoría', 'Marca', 'Bodega', 'Cantidad', 'Stock Min', 'Stock Max'])
        
        for row in data:
            writer.writerow([
                row.sku, row.name, row.cost, row.price1,
                row.category or '', row.brand or '', row.warehouse,
                row.quantity, row.min_stock, row.max_stock
            ])
    
    elif report_type == 'sales':
        # Export sales report
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        query = text("""
            SELECT s.invoice_number, s.created_at, c.name as customer,
                   s.subtotal, s.tax_amount, s.discount_amount, s.total,
                   s.payment_method, w.name as warehouse
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.id
            JOIN warehouses w ON s.warehouse_id = w.id
            WHERE s.created_at >= :start_date AND s.created_at <= :end_date
            ORDER BY s.created_at DESC
        """)
        
        data = db.session.execute(query, {
            "start_date": start_date,
            "end_date": end_date + ' 23:59:59'
        }).fetchall()
        
        writer = csv.writer(output)
        writer.writerow(['Factura', 'Fecha', 'Cliente', 'Subtotal', 'Impuesto', 'Descuento', 'Total', 'Método Pago', 'Bodega'])
        
        for row in data:
            writer.writerow([
                row.invoice_number, row.created_at, row.customer or 'Cliente General',
                row.subtotal, row.tax_amount, row.discount_amount, row.total,
                row.payment_method, row.warehouse
            ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={report_type}_report.csv'
    
    return response
