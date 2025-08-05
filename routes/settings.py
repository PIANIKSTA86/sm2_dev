from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import login_required, admin_required
from models import Setting, Warehouse, Category, Brand, ProductGroup, ProductLine, db
from utils.backup import create_backup, restore_backup
import os

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
@login_required
def index():
    return render_template('settings/index.html')

@settings_bp.route('/warehouses')
@admin_required
def warehouses():
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

@settings_bp.route('/brands')
@admin_required
def brands():
    brands = Brand.query.all()
    return render_template('settings/brands.html', brands=brands)

@settings_bp.route('/brand/new', methods=['POST'])
@admin_required
def new_brand():
    try:
        brand = Brand(
            name=request.form['name'],
            description=request.form.get('description')
        )
        
        db.session.add(brand)
        db.session.commit()
        
        flash('Marca creada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear marca: {str(e)}', 'error')
    
    return redirect(url_for('settings.brands'))

@settings_bp.route('/backup')
@admin_required
def backup():
    return render_template('settings/backup.html')

@settings_bp.route('/create_backup', methods=['POST'])
@admin_required
def create_backup_route():
    try:
        backup_file = create_backup()
        flash(f'Backup creado exitosamente: {backup_file}', 'success')
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
    settings = Setting.query.filter_by(category='company').all()
    for setting in settings:
        company_settings[setting.key] = setting.value
    
    return render_template('settings/company.html', settings=company_settings)
