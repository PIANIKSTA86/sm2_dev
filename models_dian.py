"""
Modelos para integración con facturación electrónica DIAN Colombia
"""
from app import db
from datetime import datetime
from sqlalchemy import Index

class DianTaxProvider(db.Model):
    """Proveedores Tecnológicos Autorizados DIAN"""
    __tablename__ = 'dian_tax_providers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    nit = db.Column(db.String(20), unique=True, nullable=False)
    authorized_by_dian = db.Column(db.Boolean, default=False)
    api_url = db.Column(db.String(500))  # URL del API del proveedor
    api_key = db.Column(db.String(500))  # Clave de API
    api_secret = db.Column(db.String(500))  # Secret de API
    test_mode = db.Column(db.Boolean, default=True)  # Modo de pruebas
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DianTaxProvider {self.name}>'

class DianInvoiceTypes(db.Model):
    """Tipos de documentos DIAN"""
    __tablename__ = 'dian_invoice_types'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # Código DIAN
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    # Ejemplos de códigos DIAN:
    # 01 - Factura de Venta
    # 02 - Factura de Venta de Exportación
    # 03 - Factura de Contingencia
    # 04 - Factura Electrónica de Venta
    # 91 - Nota Crédito
    # 92 - Nota Débito

class DianTaxes(db.Model):
    """Impuestos y tarifas DIAN"""
    __tablename__ = 'dian_taxes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False)  # Código impuesto DIAN
    name = db.Column(db.String(100), nullable=False)
    tax_type = db.Column(db.String(20), nullable=False)  # IVA, RETEIVA, ICA, etc.
    percentage = db.Column(db.Numeric(5, 2), nullable=False)  # Porcentaje del impuesto
    is_retention = db.Column(db.Boolean, default=False)  # Si es retención
    is_active = db.Column(db.Boolean, default=True)
    
    # Ejemplos de impuestos comunes en Colombia:
    # IVA 0%, 5%, 19%
    # RETEIVA 15%
    # RETEICA según municipio
    # RETEFUENTE según concepto

class DianResolution(db.Model):
    """Resoluciones DIAN para facturación"""
    __tablename__ = 'dian_resolutions'
    
    id = db.Column(db.Integer, primary_key=True)
    resolution_number = db.Column(db.String(50), unique=True, nullable=False)
    resolution_date = db.Column(db.Date, nullable=False)
    prefix = db.Column(db.String(10), nullable=False)  # Prefijo de numeración
    start_number = db.Column(db.Integer, nullable=False)  # Numeración inicial
    end_number = db.Column(db.Integer, nullable=False)    # Numeración final
    current_number = db.Column(db.Integer, default=0)     # Numeración actual
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DianElectronicInvoice(db.Model):
    """Facturas electrónicas enviadas a DIAN"""
    __tablename__ = 'dian_electronic_invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('dian_tax_providers.id'))
    resolution_id = db.Column(db.Integer, db.ForeignKey('dian_resolutions.id'))
    
    # Datos DIAN
    cufe = db.Column(db.String(96))  # Código Único de Facturación Electrónica
    invoice_type_code = db.Column(db.String(10), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    
    # Control de estado
    status = db.Column(db.String(20), default='PENDING')  # PENDING, SENT, ACCEPTED, REJECTED
    dian_response = db.Column(db.Text)  # Respuesta completa de DIAN
    dian_uuid = db.Column(db.String(100))  # UUID asignado por DIAN
    xml_content = db.Column(db.Text)  # XML generado
    pdf_path = db.Column(db.String(500))  # Ruta del PDF generado
    
    # Fechas de control
    sent_to_dian = db.Column(db.DateTime)
    accepted_by_dian = db.Column(db.DateTime)
    customer_notified = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    sale = db.relationship('Sale', backref='dian_invoice')
    provider = db.relationship('DianTaxProvider', backref='invoices')
    resolution = db.relationship('DianResolution', backref='invoices')
    
    __table_args__ = (
        Index('idx_dian_invoice_number', 'invoice_number'),
        Index('idx_dian_cufe', 'cufe'),
        Index('idx_dian_status', 'status'),
    )

class DianConfiguration(db.Model):
    """Configuración general para DIAN"""
    __tablename__ = 'dian_configuration'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Datos de la empresa
    company_nit = db.Column(db.String(20), nullable=False)
    company_dv = db.Column(db.String(1), nullable=False)  # Dígito de verificación
    company_name = db.Column(db.String(200), nullable=False)
    company_address = db.Column(db.String(500), nullable=False)
    company_city_code = db.Column(db.String(10), nullable=False)  # Código DANE
    company_phone = db.Column(db.String(20))
    company_email = db.Column(db.String(100), nullable=False)
    
    # Configuración del proveedor activo
    active_provider_id = db.Column(db.Integer, db.ForeignKey('dian_tax_providers.id'))
    active_resolution_id = db.Column(db.Integer, db.ForeignKey('dian_resolutions.id'))
    
    # Configuraciones generales
    test_environment = db.Column(db.Boolean, default=True)
    auto_send_invoices = db.Column(db.Boolean, default=False)
    notify_customers = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    active_provider = db.relationship('DianTaxProvider', backref='configurations')
    active_resolution = db.relationship('DianResolution', backref='configurations')

# Datos iniciales para Colombia
def init_dian_data():
    """Inicializar datos básicos de DIAN"""
    
    # Tipos de documento más comunes
    invoice_types = [
        {'code': '01', 'name': 'Factura de Venta', 'description': 'Factura de venta nacional'},
        {'code': '02', 'name': 'Factura de Exportación', 'description': 'Factura de venta de exportación'},
        {'code': '03', 'name': 'Factura de Contingencia', 'description': 'Factura por contingencia'},
        {'code': '91', 'name': 'Nota Crédito', 'description': 'Nota crédito'},
        {'code': '92', 'name': 'Nota Débito', 'description': 'Nota débito'},
    ]
    
    for type_data in invoice_types:
        if not DianInvoiceTypes.query.filter_by(code=type_data['code']).first():
            invoice_type = DianInvoiceTypes(**type_data)
            db.session.add(invoice_type)
    
    # Impuestos más comunes en Colombia
    taxes = [
        {'code': '01', 'name': 'IVA 0%', 'tax_type': 'IVA', 'percentage': 0.00, 'is_retention': False},
        {'code': '02', 'name': 'IVA 5%', 'tax_type': 'IVA', 'percentage': 5.00, 'is_retention': False},
        {'code': '03', 'name': 'IVA 19%', 'tax_type': 'IVA', 'percentage': 19.00, 'is_retention': False},
        {'code': '06', 'name': 'RETEIVA 15%', 'tax_type': 'RETEIVA', 'percentage': 15.00, 'is_retention': True},
        {'code': '07', 'name': 'RETEFUENTE 3.5%', 'tax_type': 'RETEFUENTE', 'percentage': 3.50, 'is_retention': True},
        {'code': '08', 'name': 'RETEICA 1%', 'tax_type': 'RETEICA', 'percentage': 1.00, 'is_retention': True},
    ]
    
    for tax_data in taxes:
        if not DianTaxes.query.filter_by(code=tax_data['code']).first():
            tax = DianTaxes(**tax_data)
            db.session.add(tax)
    
    # Algunos proveedores tecnológicos autorizados conocidos
    providers = [
        {'name': 'SIIGO S.A', 'nit': '8005113630', 'authorized_by_dian': True},
        {'name': 'ALIADDO SAS', 'nit': '9013455235', 'authorized_by_dian': True},
        {'name': 'CARVAJAL TECNOLOGIA Y SERVICIOS S.A.S BIC', 'nit': '8300346801', 'authorized_by_dian': True},
        {'name': 'FACTURA1 S.A.S', 'nit': '9005588441', 'authorized_by_dian': True},
        {'name': 'ECOM S.A.S', 'nit': '8300455236', 'authorized_by_dian': True},
    ]
    
    for prov_data in providers:
        if not DianTaxProvider.query.filter_by(nit=prov_data['nit']).first():
            provider = DianTaxProvider(**prov_data)
            db.session.add(provider)
    
    db.session.commit()