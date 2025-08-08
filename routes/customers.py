from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import login_required
from models import Customer, Department, City, db
from utils.pagination import paginate_query
from sqlalchemy import or_

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    customer_type = request.args.get('type', '')
    
    query = Customer.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            or_(
                Customer.full_name.ilike(f'%{search}%'),
                Customer.document_number.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%')
            )
        )
    
    if customer_type:
        query = query.filter_by(type=customer_type)
    
    query = query.order_by(Customer.full_name)
    
    customers, pagination = paginate_query(query)
    
    return render_template('customers/index.html',
                         customers=customers,
                         pagination=pagination,
                         search=search,
                         customer_type=customer_type)

@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        try:
            customer = Customer(
                type=request.form['type'],
                document_type=request.form.get('document_type'),
                document_number=request.form.get('document_number'),
                first_name=request.form.get('first_name', '').strip(),
                second_name=request.form.get('second_name', '').strip(),
                first_lastname=request.form.get('first_lastname', '').strip(),
                second_lastname=request.form.get('second_lastname', '').strip(),
                company=request.form.get('company'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                mobile=request.form.get('mobile'),
                address=request.form.get('address'),
                city_id=int(request.form['city_id']) if request.form.get('city_id') else None,
                department_id=int(request.form['department_id']) if request.form.get('department_id') else None,
                country=request.form.get('country', 'Colombia'),
                credit_limit=float(request.form.get('credit_limit', 0)),
                credit_days=int(request.form.get('credit_days', 0)),
                price_level=int(request.form.get('price_level', 1))
            )
            
            # Actualizar nombre completo
            customer.update_full_name()
            
            db.session.add(customer)
            db.session.commit()
            
            flash('Cliente creado exitosamente', 'success')
            return redirect(url_for('customers.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear cliente: {str(e)}', 'error')
    
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return render_template('customers/form.html', departments=departments)

@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            customer.type = request.form['type']
            customer.document_type = request.form.get('document_type')
            customer.document_number = request.form.get('document_number')
            customer.first_name = request.form.get('first_name', '').strip()
            customer.second_name = request.form.get('second_name', '').strip()
            customer.first_lastname = request.form.get('first_lastname', '').strip()
            customer.second_lastname = request.form.get('second_lastname', '').strip()
            customer.company = request.form.get('company')
            customer.email = request.form.get('email')
            customer.phone = request.form.get('phone')
            customer.mobile = request.form.get('mobile')
            customer.address = request.form.get('address')
            customer.city_id = int(request.form['city_id']) if request.form.get('city_id') else None
            customer.department_id = int(request.form['department_id']) if request.form.get('department_id') else None
            customer.country = request.form.get('country', 'Colombia')
            customer.credit_limit = float(request.form.get('credit_limit', 0))
            customer.credit_days = int(request.form.get('credit_days', 0))
            customer.price_level = int(request.form.get('price_level', 1))
            
            # Actualizar nombre completo
            customer.update_full_name()
            
            db.session.commit()
            
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('customers.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar cliente: {str(e)}', 'error')
    
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return render_template('customers/form.html', customer=customer, departments=departments)

@customers_bp.route('/<int:id>/toggle_status', methods=['POST'])
@login_required
def toggle_status(id):
    customer = Customer.query.get_or_404(id)
    customer.is_active = not customer.is_active
    
    try:
        db.session.commit()
        status = 'activado' if customer.is_active else 'desactivado'
        flash(f'Cliente {status} exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(url_for('customers.index'))

@customers_bp.route('/<int:id>')
@login_required
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    
    # Get customer's sales and purchases
    from models import Sale, Purchase
    
    recent_sales = Sale.query.filter_by(customer_id=id)\
                            .order_by(Sale.created_at.desc())\
                            .limit(10).all()
    
    recent_purchases = Purchase.query.filter_by(supplier_id=id)\
                                   .order_by(Purchase.created_at.desc())\
                                   .limit(10).all()
    
    return render_template('customers/view.html',
                         customer=customer,
                         recent_sales=recent_sales,
                         recent_purchases=recent_purchases)

@customers_bp.route('/api/cities/<int:department_id>')
@login_required
def get_cities(department_id):
    """API endpoint para obtener ciudades por departamento"""
    cities = City.query.filter_by(department_id=department_id, is_active=True).order_by(City.name).all()
    return {'cities': [{'id': city.id, 'name': city.name} for city in cities]}
