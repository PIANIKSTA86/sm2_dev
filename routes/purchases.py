from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from auth import login_required, get_current_user
from models import Purchase, PurchaseDetail, Customer, Product, Warehouse, Inventory, db
from utils.pagination import paginate_query
from datetime import datetime
import json

purchases_bp = Blueprint('purchases', __name__)

@purchases_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    supplier_id = request.args.get('supplier_id', type=int)
    
    query = Purchase.query.join(Customer, Purchase.supplier_id == Customer.id)
    
    if search:
        query = query.filter(Purchase.invoice_number.ilike(f'%{search}%'))
    
    if start_date:
        query = query.filter(Purchase.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    
    if end_date:
        query = query.filter(Purchase.created_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    
    query = query.order_by(Purchase.created_at.desc())
    
    purchases, pagination = paginate_query(query)
    suppliers = Customer.query.filter_by(type='supplier', is_active=True).all()
    
    return render_template('purchases/index.html',
                         purchases=purchases,
                         pagination=pagination,
                         suppliers=suppliers,
                         search=search,
                         start_date=start_date,
                         end_date=end_date,
                         supplier_id=supplier_id)

@purchases_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_purchase():
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            purchase = Purchase(
                invoice_number=request.form['invoice_number'],
                supplier_id=int(request.form['supplier_id']),
                warehouse_id=int(request.form['warehouse_id']),
                user_id=user.id,
                payment_status=request.form['payment_status'],
                notes=request.form.get('notes')
            )
            
            db.session.add(purchase)
            db.session.flush()
            
            # Process purchase details
            products_data = json.loads(request.form['products_data'])
            subtotal = 0
            
            for item in products_data:
                total_line = float(item['quantity']) * float(item['unit_cost'])
                
                detail = PurchaseDetail(
                    purchase_id=purchase.id,
                    product_id=item['product_id'],
                    quantity=float(item['quantity']),
                    unit_cost=float(item['unit_cost']),
                    total=total_line
                )
                
                db.session.add(detail)
                
                # Update inventory
                inventory = Inventory.query.filter_by(
                    product_id=item['product_id'],
                    warehouse_id=purchase.warehouse_id
                ).first()
                
                if inventory:
                    inventory.quantity += float(item['quantity'])
                    inventory.last_updated = datetime.utcnow()
                else:
                    # Create inventory record if it doesn't exist
                    inventory = Inventory(
                        product_id=item['product_id'],
                        warehouse_id=purchase.warehouse_id,
                        quantity=float(item['quantity'])
                    )
                    db.session.add(inventory)
                
                # Update product cost
                product = Product.query.get(item['product_id'])
                if product:
                    product.cost = float(item['unit_cost'])
                
                subtotal += total_line
            
            # Calculate totals
            tax_rate = float(request.form.get('tax_rate', 0)) / 100
            
            purchase.subtotal = subtotal
            purchase.tax_amount = subtotal * tax_rate
            purchase.total = subtotal + purchase.tax_amount
            
            db.session.commit()
            
            flash('Compra registrada exitosamente', 'success')
            return redirect(url_for('purchases.view_purchase', id=purchase.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar compra: {str(e)}', 'error')
    
    suppliers = Customer.query.filter_by(type='supplier', is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    return render_template('purchases/form.html',
                         suppliers=suppliers,
                         warehouses=warehouses)

@purchases_bp.route('/<int:id>')
@login_required
def view_purchase(id):
    purchase = Purchase.query.get_or_404(id)
    return render_template('purchases/view.html', purchase=purchase)

@purchases_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_purchase(id):
    purchase = Purchase.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            purchase.invoice_number = request.form['invoice_number']
            purchase.supplier_id = int(request.form['supplier_id'])
            purchase.warehouse_id = int(request.form['warehouse_id'])
            purchase.payment_status = request.form['payment_status']
            purchase.notes = request.form.get('notes')
            
            db.session.commit()
            flash('Compra actualizada exitosamente', 'success')
            return redirect(url_for('purchases.view_purchase', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar compra: {str(e)}', 'error')
    
    suppliers = Customer.query.filter_by(type='supplier', is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    return render_template('purchases/form.html',
                         purchase=purchase,
                         suppliers=suppliers,
                         warehouses=warehouses)
