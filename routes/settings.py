from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from auth import login_required, admin_required
from models import Setting, Warehouse, Category, Brand, ProductGroup, ProductLine, db
from utils.backup import create_backup, restore_backup
import os

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
@login_required
def index():
    return render_template('settings/index.html')

@settings_bp.route('/electronic_signature', methods=['GET', 'POST'])
@login_required
def electronic_signature():
    """Configuración de requisitos de firma electrónica para documentos"""
    if request.method == 'POST':
        try:
            # Configuraciones de firma electrónica
            signature_settings = [
                ('require_electronic_signature', request.form.get('require_electronic_signature') == 'on'),
                ('signature_certificate_path', request.form.get('signature_certificate_path', '')),
                ('signature_certificate_password', request.form.get('signature_certificate_password', '')),
                ('signature_provider', request.form.get('signature_provider', '')),
                ('signature_timestamp_server', request.form.get('signature_timestamp_server', '')),
                ('signature_algorithm', request.form.get('signature_algorithm', 'SHA-256')),
                ('validate_certificate', request.form.get('validate_certificate') == 'on'),
                ('require_timestamp', request.form.get('require_timestamp') == 'on'),
                ('certificate_subject', request.form.get('certificate_subject', '')),
                ('certificate_issuer', request.form.get('certificate_issuer', '')),
                ('signature_reason', request.form.get('signature_reason', 'Documento electrónico validado por SM2 Cloud')),
                ('signature_location', request.form.get('signature_location', ''))
            ]
            
            for key, value in signature_settings:
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = str(value) if not isinstance(value, bool) else ('true' if value else 'false')
                else:
                    setting = Setting(key=key, value=str(value) if not isinstance(value, bool) else ('true' if value else 'false'), category='electronic_signature')
                    db.session.add(setting)
            
            db.session.commit()
            flash('Configuración de firma electrónica actualizada exitosamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar configuración: {str(e)}', 'error')
    
    # Obtener configuraciones actuales
    signature_settings = {}
    settings = Setting.query.filter_by(category='electronic_signature').all()
    for setting in settings:
        if setting.value.lower() in ['true', 'false']:
            signature_settings[setting.key] = setting.value.lower() == 'true'
        else:
            signature_settings[setting.key] = setting.value
    
    return render_template('settings/electronic_signature.html', settings=signature_settings)

@settings_bp.route('/warehouses', methods=['GET', 'POST'])
@admin_required
def warehouses():
    if request.method == 'POST':
        try:
            warehouse_id = request.form.get('warehouse_id')
            if warehouse_id:
                # Edit existing warehouse
                warehouse = Warehouse.query.get_or_404(warehouse_id)
                warehouse.name = request.form['name']
                warehouse.address = request.form.get('address')
                warehouse.manager = request.form.get('manager')
                warehouse.phone = request.form.get('phone')
                warehouse.email = request.form.get('email')
                warehouse.is_active = bool(request.form.get('is_active'))
                flash('Bodega actualizada exitosamente', 'success')
            else:
                # Create new warehouse
                warehouse = Warehouse(
                    name=request.form['name'],
                    address=request.form.get('address'),
                    manager=request.form.get('manager'),
                    phone=request.form.get('phone'),
                    email=request.form.get('email'),
                    is_active=bool(request.form.get('is_active', True))
                )
                db.session.add(warehouse)
                flash('Bodega creada exitosamente', 'success')
            
            db.session.commit()
            return redirect(url_for('settings.warehouses'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar bodega: {str(e)}', 'error')
    
    warehouses = Warehouse.query.all()
    return render_template('settings/warehouses.html', warehouses=warehouses)

@settings_bp.route('/warehouse/new', methods=['GET', 'POST'])
@admin_required
def new_warehouse():
    if request.method == 'POST':
        try:
            warehouse = Warehouse(
                name=request.form['name'],
                code=request.form['code'],
                address=request.form.get('address'),
                phone=request.form.get('phone')
            )
            
            db.session.add(warehouse)
            db.session.commit()
            
            flash('Bodega creada exitosamente', 'success')
            return redirect(url_for('settings.warehouses'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear bodega: {str(e)}', 'error')
    
    return render_template('settings/warehouse_form.html')

@settings_bp.route('/warehouse/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_warehouse(id):
    warehouse = Warehouse.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            warehouse.name = request.form['name']
            warehouse.code = request.form['code']
            warehouse.address = request.form.get('address')
            warehouse.phone = request.form.get('phone')
            
            db.session.commit()
            
            flash('Bodega actualizada exitosamente', 'success')
            return redirect(url_for('settings.warehouses'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar bodega: {str(e)}', 'error')
    
    return render_template('settings/warehouse_form.html', warehouse=warehouse)

@settings_bp.route('/categories')
@admin_required
def categories():
    categories = Category.query.all()
    return render_template('settings/categories.html', categories=categories)

@settings_bp.route('/brands', methods=['GET', 'POST'])
@admin_required
def brands():
    if request.method == 'POST':
        try:
            brand_id = request.form.get('brand_id')
            if brand_id:
                # Edit existing brand
                brand = Brand.query.get_or_404(brand_id)
                brand.name = request.form['name']
                brand.description = request.form.get('description')
                brand.is_active = bool(request.form.get('is_active'))
                flash('Marca actualizada exitosamente', 'success')
            else:
                # Create new brand
                brand = Brand(
                    name=request.form['name'],
                    description=request.form.get('description'),
                    is_active=bool(request.form.get('is_active', True))
                )
                db.session.add(brand)
                flash('Marca creada exitosamente', 'success')
            
            db.session.commit()
            return redirect(url_for('settings.brands'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar marca: {str(e)}', 'error')
    
    brands = Brand.query.all()
    return render_template('settings/brands.html', brands=brands)

@settings_bp.route('/category/new', methods=['POST'])
@admin_required
def new_category():
    try:
        category = Category(
            name=request.form['name'],
            description=request.form.get('description')
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Categoría creada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear categoría: {str(e)}', 'error')
    
    return redirect(url_for('settings.categories'))



@settings_bp.route('/backup')
@admin_required
def backup():
    return render_template('settings/backup.html')

@settings_bp.route('/create_backup', methods=['POST'])
@admin_required
def create_backup_route():
    try:
        backup_filename = create_backup()
        backup_path = f'/tmp/{backup_filename}'
        
        # Return the file for download
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/json'
        )
    except Exception as e:
        flash(f'Error al crear backup: {str(e)}', 'error')
        return redirect(url_for('settings.backup'))

@settings_bp.route('/restore_backup', methods=['POST'])
@admin_required
def restore_backup_route():
    if 'backup_file' not in request.files:
        flash('No se seleccionó archivo', 'error')
        return redirect(url_for('settings.backup'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('No se seleccionó archivo', 'error')
        return redirect(url_for('settings.backup'))
    
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        restore_backup(temp_path)
        
        # Clean up temp file
        os.remove(temp_path)
        
        flash('Backup restaurado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al restaurar backup: {str(e)}', 'error')
    
    return redirect(url_for('settings.backup'))

@settings_bp.route('/company', methods=['GET', 'POST'])
@admin_required
def company():
    if request.method == 'POST':
        try:
            # Save company settings
            settings_to_save = [
                ('company_name', request.form.get('company_name', '')),
                ('company_address', request.form.get('company_address', '')),
                ('company_phone', request.form.get('company_phone', '')),
                ('company_email', request.form.get('company_email', '')),
                ('company_tax_id', request.form.get('company_tax_id', '')),
                ('tax_rate', request.form.get('tax_rate', '0')),
                ('currency_symbol', request.form.get('currency_symbol', '$')),
                ('invoice_footer', request.form.get('invoice_footer', ''))
            ]
            
            for key, value in settings_to_save:
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    setting = Setting(key=key, value=value, category='company')
                    db.session.add(setting)
            
            db.session.commit()
            flash('Configuración de empresa actualizada exitosamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar configuración: {str(e)}', 'error')
    
    # Get current settings
    company_settings = {}
    settings = Setting.query.all()
    for setting in settings:
        company_settings[setting.key] = setting.value
    
    # Get statistics for the sidebar
    from sqlalchemy import text
    stats = {
        'total_products': db.session.execute(text("SELECT COUNT(*) FROM products WHERE is_active = true")).scalar() or 0,
        'total_sales': db.session.execute(text("SELECT COUNT(*) FROM sales")).scalar() or 0,
        'total_customers': db.session.execute(text("SELECT COUNT(*) FROM customers")).scalar() or 0,
        'low_stock_items': db.session.execute(text("SELECT COUNT(*) FROM products p LEFT JOIN inventory i ON p.id = i.product_id WHERE p.is_active = true AND COALESCE(i.quantity, 0) <= 10")).scalar() or 0
    }
    
    return render_template('settings/company.html', settings=company_settings, stats=stats)
