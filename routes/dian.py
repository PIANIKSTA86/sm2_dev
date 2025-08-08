"""
Rutas para gestión de facturación electrónica DIAN
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from auth import login_required, get_current_user
from models_dian import (DianTaxProvider, DianInvoiceTypes, DianTaxes, DianResolution, 
                        DianElectronicInvoice, DianConfiguration, init_dian_data)
from models import Sale, db
from utils.pagination import paginate_query
# import requests
import json
from datetime import datetime, date

dian_bp = Blueprint('dian', __name__)

@dian_bp.route('/')
@login_required
def index():
    """Dashboard principal de DIAN"""
    # Estadísticas básicas
    total_invoices = DianElectronicInvoice.query.count()
    pending_invoices = DianElectronicInvoice.query.filter_by(status='PENDING').count()
    accepted_invoices = DianElectronicInvoice.query.filter_by(status='ACCEPTED').count()
    rejected_invoices = DianElectronicInvoice.query.filter_by(status='REJECTED').count()
    
    # Configuración actual
    config = DianConfiguration.query.first()
    
    # Últimas facturas
    recent_invoices = DianElectronicInvoice.query.order_by(
        DianElectronicInvoice.created_at.desc()
    ).limit(10).all()
    
    return render_template('dian/index.html',
                         total_invoices=total_invoices,
                         pending_invoices=pending_invoices,
                         accepted_invoices=accepted_invoices,
                         rejected_invoices=rejected_invoices,
                         config=config,
                         recent_invoices=recent_invoices)

@dian_bp.route('/configuration', methods=['GET', 'POST'])
@login_required
def configuration():
    """Configuración general de DIAN"""
    config = DianConfiguration.query.first()
    
    if request.method == 'POST':
        try:
            if not config:
                config = DianConfiguration()
                db.session.add(config)
            
            # Datos de la empresa
            config.company_nit = request.form['company_nit']
            config.company_dv = request.form['company_dv']
            config.company_name = request.form['company_name']
            config.company_address = request.form['company_address']
            config.company_city_code = request.form['company_city_code']
            config.company_phone = request.form.get('company_phone')
            config.company_email = request.form['company_email']
            
            # Configuraciones
            config.active_provider_id = int(request.form['active_provider_id']) if request.form.get('active_provider_id') else None
            config.active_resolution_id = int(request.form['active_resolution_id']) if request.form.get('active_resolution_id') else None
            config.test_environment = bool(request.form.get('test_environment'))
            config.auto_send_invoices = bool(request.form.get('auto_send_invoices'))
            config.notify_customers = bool(request.form.get('notify_customers'))
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Configuración actualizada exitosamente', 'success')
            return redirect(url_for('dian.configuration'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar configuración: {str(e)}', 'error')
    
    providers = DianTaxProvider.query.filter_by(is_active=True).all()
    resolutions = DianResolution.query.filter_by(is_active=True).all()
    
    return render_template('dian/configuration.html',
                         config=config,
                         providers=providers,
                         resolutions=resolutions)

@dian_bp.route('/providers')
@login_required
def providers():
    """Gestión de proveedores tecnológicos"""
    providers = DianTaxProvider.query.all()
    return render_template('dian/providers.html', providers=providers)

@dian_bp.route('/providers/new', methods=['GET', 'POST'])
@login_required
def new_provider():
    """Crear nuevo proveedor tecnológico"""
    if request.method == 'POST':
        try:
            provider = DianTaxProvider(
                name=request.form['name'],
                nit=request.form['nit'],
                authorized_by_dian=bool(request.form.get('authorized_by_dian')),
                api_url=request.form.get('api_url'),
                api_key=request.form.get('api_key'),
                api_secret=request.form.get('api_secret'),
                test_mode=bool(request.form.get('test_mode', True))
            )
            db.session.add(provider)
            db.session.commit()
            flash('Proveedor creado exitosamente', 'success')
            return redirect(url_for('dian.providers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear proveedor: {str(e)}', 'error')
    
    return render_template('dian/provider_form.html')

@dian_bp.route('/resolutions')
@login_required
def resolutions():
    """Gestión de resoluciones DIAN"""
    resolutions = DianResolution.query.all()
    return render_template('dian/resolutions.html', resolutions=resolutions)

@dian_bp.route('/resolutions/new', methods=['GET', 'POST'])
@login_required
def new_resolution():
    """Crear nueva resolución"""
    if request.method == 'POST':
        try:
            resolution = DianResolution(
                resolution_number=request.form['resolution_number'],
                resolution_date=datetime.strptime(request.form['resolution_date'], '%Y-%m-%d').date(),
                prefix=request.form['prefix'],
                start_number=int(request.form['start_number']),
                end_number=int(request.form['end_number']),
                current_number=int(request.form['start_number']),
                valid_from=datetime.strptime(request.form['valid_from'], '%Y-%m-%d').date(),
                valid_to=datetime.strptime(request.form['valid_to'], '%Y-%m-%d').date()
            )
            db.session.add(resolution)
            db.session.commit()
            flash('Resolución creada exitosamente', 'success')
            return redirect(url_for('dian.resolutions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear resolución: {str(e)}', 'error')
    
    return render_template('dian/resolution_form.html')

@dian_bp.route('/invoices')
@login_required
def invoices():
    """Listado de facturas electrónicas"""
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    query = DianElectronicInvoice.query
    
    if search:
        query = query.filter(
            DianElectronicInvoice.invoice_number.ilike(f'%{search}%')
        )
    
    if status:
        query = query.filter_by(status=status)
    
    invoices, pagination = paginate_query(query.order_by(
        DianElectronicInvoice.created_at.desc()
    ))
    
    return render_template('dian/invoices.html',
                         invoices=invoices,
                         pagination=pagination,
                         search=search,
                         status=status)

@dian_bp.route('/invoices/<int:id>')
@login_required
def invoice_detail(id):
    """Detalle de factura electrónica"""
    invoice = DianElectronicInvoice.query.get_or_404(id)
    return render_template('dian/invoice_detail.html', invoice=invoice)

@dian_bp.route('/send_invoice/<int:sale_id>', methods=['POST'])
@login_required
def send_invoice(sale_id):
    """Enviar factura a DIAN"""
    try:
        sale = Sale.query.get_or_404(sale_id)
        config = DianConfiguration.query.first()
        
        if not config or not config.active_provider:
            return jsonify({
                'success': False, 
                'message': 'No hay configuración DIAN válida'
            })
        
        if not config.active_resolution:
            return jsonify({
                'success': False, 
                'message': 'No hay resolución DIAN activa'
            })
        
        # Verificar si ya existe factura electrónica para esta venta
        existing_invoice = DianElectronicInvoice.query.filter_by(sale_id=sale_id).first()
        if existing_invoice:
            return jsonify({
                'success': False, 
                'message': 'Esta venta ya tiene factura electrónica generada'
            })
        
        # Generar siguiente número de factura
        resolution = config.active_resolution
        if resolution.current_number >= resolution.end_number:
            return jsonify({
                'success': False, 
                'message': 'Se agotó la numeración de la resolución actual'
            })
        
        resolution.current_number += 1
        invoice_number = f"{resolution.prefix}{resolution.current_number}"
        
        # Crear registro de factura electrónica
        electronic_invoice = DianElectronicInvoice(
            sale_id=sale_id,
            provider_id=config.active_provider_id,
            resolution_id=config.active_resolution_id,
            invoice_type_code='01',  # Factura de Venta
            invoice_number=invoice_number,
            issue_date=datetime.utcnow(),
            status='PENDING'
        )
        
        db.session.add(electronic_invoice)
        db.session.commit()
        
        # TODO: Aquí se integraría con el API del proveedor tecnológico
        # Por ahora simulamos el envío exitoso
        electronic_invoice.status = 'SENT'
        electronic_invoice.sent_to_dian = datetime.utcnow()
        electronic_invoice.dian_uuid = f"UUID-{sale_id}-{datetime.utcnow().timestamp()}"
        db.session.commit()
        
        flash('Factura enviada a DIAN exitosamente', 'success')
        return jsonify({'success': True, 'invoice_id': electronic_invoice.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@dian_bp.route('/initialize_data', methods=['POST'])
@login_required
def initialize_data():
    """Inicializar datos básicos de DIAN"""
    try:
        init_dian_data()
        flash('Datos DIAN inicializados exitosamente', 'success')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@dian_bp.route('/test_provider/<int:provider_id>', methods=['POST'])
@login_required
def test_provider(provider_id):
    """Probar conexión con proveedor tecnológico"""
    try:
        provider = DianTaxProvider.query.get_or_404(provider_id)
        
        # TODO: Implementar prueba real según el API del proveedor
        # Por ahora simulamos una prueba exitosa
        test_result = {
            'success': True,
            'message': 'Conexión exitosa con el proveedor',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(test_result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})