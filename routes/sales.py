from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from auth import login_required, get_current_user
from models import Sale, SaleDetail, Customer, Product, Warehouse, Inventory, SerialNumber, db
from utils.pagination import paginate_query
from utils.pdf_generator import generate_invoice_pdf
from utils.email_service import send_invoice_email
from sqlalchemy import text, func
from datetime import datetime
import json

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    customer_id = request.args.get('customer_id', type=int)
    
    query = Sale.query.join(Customer, Sale.customer_id == Customer.id, isouter=True)
    
    if search:
        query = query.filter(Sale.invoice_number.ilike(f'%{search}%'))
    
    if start_date:
        query = query.filter(Sale.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    
    if end_date:
        query = query.filter(Sale.created_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)
    
    query = query.order_by(Sale.created_at.desc())
    
    sales, pagination = paginate_query(query)
    customers = Customer.query.filter_by(type='client', is_active=True).all()
    
    return render_template('sales/index.html',
                         sales=sales,
                         pagination=pagination,
                         customers=customers,
                         search=search,
                         start_date=start_date,
                         end_date=end_date,
                         customer_id=customer_id)

@sales_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            # Generate invoice number
            last_sale = Sale.query.order_by(Sale.id.desc()).first()
            next_number = (last_sale.id + 1) if last_sale else 1
            invoice_number = f"VEN-{next_number:06d}"
            
            # Create sale
            sale = Sale(
                invoice_number=invoice_number,
                customer_id=int(request.form['customer_id']) if request.form.get('customer_id') else None,
                warehouse_id=int(request.form['warehouse_id']),
                user_id=user.id,
                payment_method=request.form['payment_method'],
                notes=request.form.get('notes')
            )
            
            db.session.add(sale)
            db.session.flush()
            
            # Process sale details
            products_data = json.loads(request.form['products_data'])
            subtotal = 0
            
            for item in products_data:
                product = Product.query.get(item['product_id'])
                total_line = float(item['quantity']) * float(item['unit_price'])
                discount_amount = total_line * (float(item.get('discount_percent', 0)) / 100)
                total_line -= discount_amount
                
                detail = SaleDetail(
                    sale_id=sale.id,
                    product_id=item['product_id'],
                    quantity=float(item['quantity']),
                    unit_price=float(item['unit_price']),
                    discount_percent=float(item.get('discount_percent', 0)),
                    discount_amount=discount_amount,
                    total=total_line
                )
                
                db.session.add(detail)
                
                # Update inventory
                inventory = Inventory.query.filter_by(
                    product_id=item['product_id'],
                    warehouse_id=sale.warehouse_id
                ).first()
                
                if inventory:
                    inventory.quantity -= float(item['quantity'])
                    inventory.last_updated = datetime.utcnow()
                
                # Handle serial numbers
                if product.track_serial and 'serial_numbers' in item:
                    for serial in item['serial_numbers']:
                        serial_record = SerialNumber.query.get(serial['id'])
                        if serial_record:
                            serial_record.status = 'sold'
                            detail.serial_id = serial_record.id
                
                subtotal += total_line
            
            # Calculate totals
            tax_rate = float(request.form.get('tax_rate', 0)) / 100
            discount_percent = float(request.form.get('discount_percent', 0)) / 100
            
            sale.subtotal = subtotal
            sale.discount_amount = subtotal * discount_percent
            sale.tax_amount = (subtotal - sale.discount_amount) * tax_rate
            sale.total = subtotal - sale.discount_amount + sale.tax_amount
            
            db.session.commit()
            
            flash('Venta registrada exitosamente', 'success')
            
            # Generate and email invoice if requested
            if request.form.get('send_email') and sale.customer and sale.customer.email:
                try:
                    pdf_data = generate_invoice_pdf(sale)
                    send_invoice_email(sale.customer.email, sale, pdf_data)
                    flash('Factura enviada por email', 'info')
                except Exception as e:
                    flash(f'Error al enviar email: {str(e)}', 'warning')
            
            return redirect(url_for('sales.view_sale', id=sale.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar venta: {str(e)}', 'error')
    
    customers = Customer.query.filter_by(type='client', is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    return render_template('sales/form.html',
                         customers=customers,
                         warehouses=warehouses)

@sales_bp.route('/<int:id>')
@login_required
def view_sale(id):
    sale = Sale.query.get_or_404(id)
    return render_template('sales/view.html', sale=sale)

@sales_bp.route('/<int:id>/pdf')
@login_required
def generate_pdf(id):
    sale = Sale.query.get_or_404(id)
    return generate_invoice_pdf(sale, download=True)

@sales_bp.route('/<int:id>/email', methods=['POST'])
@login_required
def email_invoice(id):
    sale = Sale.query.get_or_404(id)
    email = request.form.get('email')
    
    if not email:
        flash('Email requerido', 'error')
        return redirect(url_for('sales.view_sale', id=id))
    
    try:
        pdf_data = generate_invoice_pdf(sale)
        send_invoice_email(email, sale, pdf_data)
        flash('Factura enviada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al enviar email: {str(e)}', 'error')
    
    return redirect(url_for('sales.view_sale', id=id))

@sales_bp.route('/get_customer_info/<int:customer_id>')
@login_required
def get_customer_info(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    return jsonify({
        'name': customer.name,
        'email': customer.email,
        'phone': customer.phone,
        'address': customer.address,
        'price_level': customer.price_level,
        'credit_limit': float(customer.credit_limit),
        'credit_days': customer.credit_days
    })

@sales_bp.route('/get_serials/<int:product_id>/<int:warehouse_id>')
@login_required
def get_serials(product_id, warehouse_id):
    serials = SerialNumber.query.filter_by(
        product_id=product_id,
        warehouse_id=warehouse_id,
        status='available'
    ).all()
    
    return jsonify([{
        'id': s.id,
        'serial_imei': s.serial_imei
    } for s in serials])
