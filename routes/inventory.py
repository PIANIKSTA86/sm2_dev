from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from auth import login_required, get_current_user
from models import Product, Category, Brand, ProductGroup, ProductLine, Warehouse, Inventory, SerialNumber, db
from utils.pagination import paginate_query
from sqlalchemy import or_, text
from app import cache
import json

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
@login_required
def index():
    user = get_current_user()
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    brand_id = request.args.get('brand_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    
    # Build query with filters
    query = db.session.query(Product).filter_by(is_active=True)
    
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f'%{search}%'),
                Product.sku.ilike(f'%{search}%'),
                Product.barcode.ilike(f'%{search}%')
            )
        )
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    
    # Get filter options
    categories = Category.query.filter_by(is_active=True).all()
    brands = Brand.query.filter_by(is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    # Paginate results
    products, pagination = paginate_query(query, per_page=20)
    
    # Get inventory data for each product
    if warehouse_id:
        inventory_query = text("""
            SELECT product_id, SUM(quantity) as total_quantity
            FROM inventory 
            WHERE warehouse_id = :warehouse_id
            GROUP BY product_id
        """)
        inventory_data = db.session.execute(inventory_query, {"warehouse_id": warehouse_id}).fetchall()
    else:
        inventory_query = text("""
            SELECT product_id, SUM(quantity) as total_quantity
            FROM inventory 
            GROUP BY product_id
        """)
        inventory_data = db.session.execute(inventory_query).fetchall()
    
    inventory_dict = {row.product_id: row.total_quantity for row in inventory_data}
    
    return render_template('inventory/index.html',
                         products=products,
                         pagination=pagination,
                         categories=categories,
                         brands=brands,
                         warehouses=warehouses,
                         inventory_dict=inventory_dict,
                         search=search,
                         category_id=category_id,
                         brand_id=brand_id,
                         warehouse_id=warehouse_id)

@inventory_bp.route('/product/new', methods=['GET', 'POST'])
@login_required
def new_product():
    if request.method == 'POST':
        try:
            product = Product(
                sku=request.form['sku'],
                barcode=request.form.get('barcode') or None,
                name=request.form['name'],
                description=request.form.get('description'),
                unit_measure=request.form['unit_measure'],
                cost=float(request.form.get('cost', 0)),
                price1=float(request.form.get('price1', 0)),
                price2=float(request.form.get('price2', 0)),
                price3=float(request.form.get('price3', 0)),
                price4=float(request.form.get('price4', 0)),
                category_id=int(request.form['category_id']) if request.form.get('category_id') else None,
                brand_id=int(request.form['brand_id']) if request.form.get('brand_id') else None,
                group_id=int(request.form['group_id']) if request.form.get('group_id') else None,
                line_id=int(request.form['line_id']) if request.form.get('line_id') else None,
                is_service=bool(request.form.get('is_service')),
                track_serial=bool(request.form.get('track_serial'))
            )
            
            db.session.add(product)
            db.session.flush()  # Get the product ID
            
            # Create inventory records for all warehouses
            warehouses = Warehouse.query.filter_by(is_active=True).all()
            for warehouse in warehouses:
                inventory = Inventory(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    quantity=0,
                    min_stock=float(request.form.get('min_stock', 0)),
                    max_stock=float(request.form.get('max_stock', 0))
                )
                db.session.add(inventory)
            
            db.session.commit()
            cache.clear()  # Clear cache after changes
            flash('Producto creado exitosamente', 'success')
            return redirect(url_for('inventory.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear producto: {str(e)}', 'error')
    
    categories = Category.query.filter_by(is_active=True).all()
    brands = Brand.query.filter_by(is_active=True).all()
    groups = ProductGroup.query.filter_by(is_active=True).all()
    lines = ProductLine.query.filter_by(is_active=True).all()
    
    return render_template('inventory/form.html',
                         categories=categories,
                         brands=brands,
                         groups=groups,
                         lines=lines)

@inventory_bp.route('/product/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            product.sku = request.form['sku']
            product.barcode = request.form.get('barcode') or None
            product.name = request.form['name']
            product.description = request.form.get('description')
            product.unit_measure = request.form['unit_measure']
            product.cost = float(request.form.get('cost', 0))
            product.price1 = float(request.form.get('price1', 0))
            product.price2 = float(request.form.get('price2', 0))
            product.price3 = float(request.form.get('price3', 0))
            product.price4 = float(request.form.get('price4', 0))
            product.category_id = int(request.form['category_id']) if request.form.get('category_id') else None
            product.brand_id = int(request.form['brand_id']) if request.form.get('brand_id') else None
            product.group_id = int(request.form['group_id']) if request.form.get('group_id') else None
            product.line_id = int(request.form['line_id']) if request.form.get('line_id') else None
            product.is_service = bool(request.form.get('is_service'))
            product.track_serial = bool(request.form.get('track_serial'))
            
            db.session.commit()
            cache.clear()
            flash('Producto actualizado exitosamente', 'success')
            return redirect(url_for('inventory.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar producto: {str(e)}', 'error')
    
    categories = Category.query.filter_by(is_active=True).all()
    brands = Brand.query.filter_by(is_active=True).all()
    groups = ProductGroup.query.filter_by(is_active=True).all()
    lines = ProductLine.query.filter_by(is_active=True).all()
    
    return render_template('inventory/form.html',
                         product=product,
                         categories=categories,
                         brands=brands,
                         groups=groups,
                         lines=lines)

@inventory_bp.route('/product/<int:id>/inventory')
@login_required
def product_inventory(id):
    product = Product.query.get_or_404(id)
    inventory_records = Inventory.query.filter_by(product_id=id).join(Warehouse).all()
    
    return render_template('inventory/product_inventory.html',
                         product=product,
                         inventory_records=inventory_records)

@inventory_bp.route('/search_products')
@login_required
def search_products():
    """AJAX endpoint for product search in POS and sales"""
    search = request.args.get('q', '')
    warehouse_id = request.args.get('warehouse_id', type=int)
    
    if len(search) < 2:
        return jsonify([])
    
    # Search products with inventory
    query = text("""
        SELECT p.id, p.sku, p.name, p.barcode, p.price1, p.price2, p.price3, p.price4,
               COALESCE(i.quantity, 0) as quantity, p.track_serial
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id 
        WHERE p.is_active = true 
        AND (p.name ILIKE :search OR p.sku ILIKE :search OR p.barcode ILIKE :search)
        AND (:warehouse_id IS NULL OR i.warehouse_id = :warehouse_id OR i.warehouse_id IS NULL)
        ORDER BY p.name
        LIMIT 20
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
            'track_serial': row.track_serial
        })
    
    return jsonify(products)

@inventory_bp.route('/categories')
@login_required
def categories():
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('inventory/categories.html', categories=categories)

@inventory_bp.route('/brands')
@login_required
def brands():
    brands = Brand.query.filter_by(is_active=True).all()
    return render_template('inventory/brands.html', brands=brands)

@inventory_bp.route('/transfers')
@login_required
def transfers():
    """Warehouse transfer management"""
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    transfers = []  # TODO: Implement transfer model
    return render_template('inventory/transfers.html', 
                         warehouses=warehouses, 
                         transfers=transfers)

@inventory_bp.route('/stock_levels')
@login_required
def stock_levels():
    """Stock levels across warehouses"""
    warehouse_id = request.args.get('warehouse_id', type=int)
    
    # Get stock levels query
    if warehouse_id:
        query = text("""
            SELECT p.id, p.sku, p.name, w.name as warehouse_name, 
                   COALESCE(i.quantity, 0) as quantity, p.min_stock
            FROM products p
            CROSS JOIN warehouses w
            LEFT JOIN inventory i ON p.id = i.product_id AND w.id = i.warehouse_id
            WHERE p.is_active = true AND w.is_active = true AND w.id = :warehouse_id
            ORDER BY p.name, w.name
        """)
        stock_data = db.session.execute(query, {"warehouse_id": warehouse_id}).fetchall()
    else:
        query = text("""
            SELECT p.id, p.sku, p.name, w.name as warehouse_name, 
                   COALESCE(i.quantity, 0) as quantity, p.min_stock
            FROM products p
            CROSS JOIN warehouses w
            LEFT JOIN inventory i ON p.id = i.product_id AND w.id = i.warehouse_id
            WHERE p.is_active = true AND w.is_active = true
            ORDER BY p.name, w.name
        """)
        stock_data = db.session.execute(query).fetchall()
    
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    return render_template('inventory/stock_levels.html',
                         stock_data=stock_data,
                         warehouses=warehouses,
                         selected_warehouse=warehouse_id)
