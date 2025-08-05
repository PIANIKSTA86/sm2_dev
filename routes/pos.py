from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, get_current_user
from models import Sale, SaleDetail, Customer, Product, Warehouse, Inventory, SerialNumber, db
from utils.pdf_generator import generate_invoice_pdf
from datetime import datetime
import json

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/')
@login_required
def index():
    user = get_current_user()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    # Get or set default warehouse
    default_warehouse_id = session.get('pos_warehouse_id')
    if not default_warehouse_id and warehouses:
        default_warehouse_id = warehouses[0].id
        session['pos_warehouse_id'] = default_warehouse_id
    
    # Get recent customers for quick selection
    recent_customers = Customer.query.filter_by(type='client', is_active=True)\
                                   .order_by(Customer.created_at.desc())\
                                   .limit(10).all()
    
    return render_template('pos/index.html',
                         warehouses=warehouses,
                         recent_customers=recent_customers,
                         default_warehouse_id=default_warehouse_id)

@pos_bp.route('/set_warehouse', methods=['POST'])
@login_required
def set_warehouse():
    warehouse_id = request.form.get('warehouse_id', type=int)
    if warehouse_id:
        session['pos_warehouse_id'] = warehouse_id
        flash('Bodega seleccionada', 'success')
    return redirect(url_for('pos.index'))

@pos_bp.route('/search_product')
@login_required
def search_product():
    """Quick product search for POS"""
    search = request.args.get('q', '').strip()
    warehouse_id = session.get('pos_warehouse_id')
    
    if len(search) < 1:
        return jsonify({'products': []})
    
    # Try exact barcode match first
    product = db.session.query(Product)\
                .filter(Product.barcode == search, Product.is_active == True)\
                .first()
    
    if product:
        # Get inventory for this product
        inventory = Inventory.query.filter_by(
            product_id=product.id,
            warehouse_id=warehouse_id
        ).first()
        
        quantity = inventory.quantity if inventory else 0
        
        return jsonify({
            'products': [{
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'barcode': product.barcode,
                'price1': float(product.price1 or 0),
                'price2': float(product.price2 or 0),
                'price3': float(product.price3 or 0),
                'price4': float(product.price4 or 0),
                'quantity': float(quantity),
                'track_serial': product.track_serial,
                'exact_match': True
            }]
        })
    
    # Search by name or SKU
    from sqlalchemy import text
    query = text("""
        SELECT p.id, p.sku, p.name, p.barcode, p.price1, p.price2, p.price3, p.price4,
               COALESCE(i.quantity, 0) as quantity, p.track_serial
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id AND i.warehouse_id = :warehouse_id
        WHERE p.is_active = true 
        AND (p.name ILIKE :search OR p.sku ILIKE :search)
        ORDER BY p.name
        LIMIT 10
    """)
    
    results = db.session.execute(query, {
        "search": f"%{search}%",
        "warehouse_id": warehouse_id
    }).fetchall()
    
    products = []
    for row in results:
        products.append({
            'id': row.id,
            'sku': row.sku,
            'name': row.name,
            'barcode': row.barcode,
            'price1': float(row.price1 or 0),
            'price2': float(row.price2 or 0),
            'price3': float(row.price3 or 0),
            'price4': float(row.price4 or 0),
            'quantity': float(row.quantity or 0),
            'track_serial': row.track_serial,
            'exact_match': False
        })
    
    return jsonify({'products': products})

@pos_bp.route('/process_sale', methods=['POST'])
@login_required
def process_sale():
    user = get_current_user()
    warehouse_id = session.get('pos_warehouse_id')
    
    if not warehouse_id:
        return jsonify({'success': False, 'error': 'Seleccione una bodega'})
    
    try:
        data = request.get_json()
        
        # Generate invoice number
        last_sale = Sale.query.order_by(Sale.id.desc()).first()
        next_number = (last_sale.id + 1) if last_sale else 1
        invoice_number = f"POS-{next_number:06d}"
        
        # Create sale
        sale = Sale(
            invoice_number=invoice_number,
            customer_id=data.get('customer_id'),
            warehouse_id=warehouse_id,
            user_id=user.id,
            payment_method=data.get('payment_method', 'cash'),
            subtotal=float(data['subtotal']),
            tax_amount=float(data.get('tax_amount', 0)),
            discount_amount=float(data.get('discount_amount', 0)),
            total=float(data['total'])
        )
        
        db.session.add(sale)
        db.session.flush()
        
        # Process sale details
        for item in data['items']:
            detail = SaleDetail(
                sale_id=sale.id,
                product_id=item['product_id'],
                quantity=float(item['quantity']),
                unit_price=float(item['unit_price']),
                discount_percent=float(item.get('discount_percent', 0)),
                discount_amount=float(item.get('discount_amount', 0)),
                total=float(item['total'])
            )
            
            db.session.add(detail)
            
            # Update inventory
            inventory = Inventory.query.filter_by(
                product_id=item['product_id'],
                warehouse_id=warehouse_id
            ).first()
            
            if inventory:
                inventory.quantity -= float(item['quantity'])
                inventory.last_updated = datetime.utcnow()
            
            # Handle serial numbers if provided
            if 'serial_id' in item and item['serial_id']:
                serial = SerialNumber.query.get(item['serial_id'])
                if serial:
                    serial.status = 'sold'
                    detail.serial_id = serial.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'invoice_number': sale.invoice_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@pos_bp.route('/get_customer/<int:customer_id>')
@login_required
def get_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    return jsonify({
        'id': customer.id,
        'name': customer.name,
        'email': customer.email,
        'phone': customer.phone,
        'price_level': customer.price_level
    })

@pos_bp.route('/quick_customer', methods=['POST'])
@login_required
def quick_customer():
    """Create a quick customer for POS sales"""
    data = request.get_json()
    
    try:
        customer = Customer(
            type='client',
            name=data['name'],
            document_number=data.get('document'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'price_level': customer.price_level
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@pos_bp.route('/recent_sales')
@login_required
def recent_sales():
    """Get recent sales for current user and warehouse"""
    warehouse_id = session.get('pos_warehouse_id')
    user = get_current_user()
    
    sales = Sale.query.filter_by(warehouse_id=warehouse_id)\
                     .order_by(Sale.created_at.desc())\
                     .limit(10).all()
    
    return render_template('pos/recent_sales.html', sales=sales)

@pos_bp.route('/reprint/<int:sale_id>')
@login_required
def reprint_invoice(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return generate_invoice_pdf(sale, download=True)
