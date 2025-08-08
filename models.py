from app import db
from datetime import datetime
from sqlalchemy import Index, text
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, manager, employee
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'))
    is_active = db.Column(db.Boolean, default=True)
    theme = db.Column(db.String(20), default='blue')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    warehouse = db.relationship('Warehouse', backref='users')

class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class Brand(db.Model):
    __tablename__ = 'brands'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class ProductGroup(db.Model):
    __tablename__ = 'product_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class ProductLine(db.Model):
    __tablename__ = 'product_lines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unit_measure = db.Column(db.String(20), nullable=False)  # unidad, kg, lt, etc.
    cost = db.Column(db.Numeric(10, 2), default=0)
    price1 = db.Column(db.Numeric(10, 2), default=0)  # Precio público
    price2 = db.Column(db.Numeric(10, 2), default=0)  # Precio mayorista
    price3 = db.Column(db.Numeric(10, 2), default=0)  # Precio distribuidor
    price4 = db.Column(db.Numeric(10, 2), default=0)  # Precio especial
    
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('product_groups.id'))
    line_id = db.Column(db.Integer, db.ForeignKey('product_lines.id'))
    
    is_service = db.Column(db.Boolean, default=False)
    track_serial = db.Column(db.Boolean, default=False)  # Rastrea serial/IMEI
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref='products')
    brand = db.relationship('Brand', backref='products')
    group = db.relationship('ProductGroup', backref='products')
    line = db.relationship('ProductLine', backref='products')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_product_search', 'name', 'sku', 'barcode'),
        Index('idx_product_category', 'category_id'),
        Index('idx_product_brand', 'brand_id'),
    )

class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), default=0)
    min_stock = db.Column(db.Numeric(10, 3), default=0)
    max_stock = db.Column(db.Numeric(10, 3), default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref='inventory_records')
    warehouse = db.relationship('Warehouse', backref='inventory_records')
    
    __table_args__ = (
        db.UniqueConstraint('product_id', 'warehouse_id'),
        Index('idx_inventory_product', 'product_id'),
        Index('idx_inventory_warehouse', 'warehouse_id'),
    )

class SerialNumber(db.Model):
    __tablename__ = 'serial_numbers'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    serial_imei = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='available')  # available, sold, reserved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref='serial_numbers')
    warehouse = db.relationship('Warehouse', backref='serial_numbers')

# Modelos geográficos para Colombia
class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(2), unique=True, nullable=False)  # Código DANE
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class City(db.Model):
    __tablename__ = 'cities'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(5), unique=True, nullable=False)  # Código DANE
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    department = db.relationship('Department', backref='cities')

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # client, supplier, employee, other
    document_type = db.Column(db.String(20))  # cedula, nit, passport, ti, ce
    document_number = db.Column(db.String(50))
    
    # Separación de nombres y apellidos
    first_name = db.Column(db.String(100))
    second_name = db.Column(db.String(100))
    first_lastname = db.Column(db.String(100))
    second_lastname = db.Column(db.String(100))
    
    # Campo calculado para nombre completo (compatible con versión anterior)
    full_name = db.Column(db.String(400))
    
    company = db.Column(db.String(200))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    address = db.Column(db.Text)
    
    # Referencias geográficas
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    country = db.Column(db.String(100), default='Colombia')
    
    credit_limit = db.Column(db.Numeric(12, 2), default=0)
    credit_days = db.Column(db.Integer, default=0)
    price_level = db.Column(db.Integer, default=1)  # 1-4 para price1-4
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    city = db.relationship('City', backref='customers')
    department = db.relationship('Department', backref='customers')
    
    def update_full_name(self):
        """Actualiza el campo full_name basado en nombres y apellidos"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.second_name:
            parts.append(self.second_name)
        if self.first_lastname:
            parts.append(self.first_lastname)
        if self.second_lastname:
            parts.append(self.second_lastname)
        self.full_name = ' '.join(parts) if parts else ''
    
    __table_args__ = (
        Index('idx_customer_search', 'full_name', 'document_number', 'email'),
        Index('idx_customer_type', 'type'),
        Index('idx_customer_location', 'city_id', 'department_id'),
    )

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    tax_amount = db.Column(db.Numeric(12, 2), default=0)
    discount_amount = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    
    payment_method = db.Column(db.String(50))  # cash, card, credit, transfer
    payment_status = db.Column(db.String(20), default='paid')  # paid, pending, partial
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    customer = db.relationship('Customer', backref='sales')
    warehouse = db.relationship('Warehouse', backref='sales')
    user = db.relationship('User', backref='sales')
    
    __table_args__ = (
        Index('idx_sale_date', 'created_at'),
        Index('idx_sale_customer', 'customer_id'),
        Index('idx_sale_warehouse', 'warehouse_id'),
    )

class SaleDetail(db.Model):
    __tablename__ = 'sale_details'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    serial_id = db.Column(db.Integer, db.ForeignKey('serial_numbers.id'))
    
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    
    sale = db.relationship('Sale', backref='details')
    product = db.relationship('Product', backref='sale_details')
    serial = db.relationship('SerialNumber', backref='sale_details')

class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    tax_amount = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    
    payment_status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    supplier = db.relationship('Customer', backref='purchases')
    warehouse = db.relationship('Warehouse', backref='purchases')
    user = db.relationship('User', backref='purchases')
    
    __table_args__ = (
        Index('idx_purchase_date', 'created_at'),
        Index('idx_purchase_supplier', 'supplier_id'),
    )

class PurchaseDetail(db.Model):
    __tablename__ = 'purchase_details'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    
    purchase = db.relationship('Purchase', backref='details')
    product = db.relationship('Product', backref='purchase_details')

class Currency(db.Model):
    __tablename__ = 'currencies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)  # ISO 4217
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    exchange_rate = db.Column(db.Numeric(10, 4), default=1.0)  # Respecto a la moneda base

class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))

# ===== MODELOS CONTABLES - SISTEMA DE PARTIDA DOBLE =====

class ChartOfAccounts(db.Model):
    """Plan Único de Cuentas Contables"""
    __tablename__ = 'chart_of_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # Ej: 1.1.01.001
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    account_type = db.Column(db.String(20), nullable=False)  # ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO
    account_subtype = db.Column(db.String(50))  # CORRIENTE, NO_CORRIENTE, etc.
    parent_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'))  # Cuenta padre
    level = db.Column(db.Integer, nullable=False, default=1)  # Nivel jerárquico
    is_detail_account = db.Column(db.Boolean, default=True)  # Si acepta movimientos
    normal_balance = db.Column(db.String(10), nullable=False)  # DEBIT o CREDIT
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    parent = db.relationship('ChartOfAccounts', remote_side=[id], backref='sub_accounts')
    
    def __repr__(self):
        return f'<Account {self.code} - {self.name}>'

class AccountingPeriod(db.Model):
    """Periodos Contables"""
    __tablename__ = 'accounting_periods'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Ej: "Enero 2024"
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer)  # Opcional para periodos anuales
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_closed = db.Column(db.Boolean, default=False)
    closed_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class JournalEntry(db.Model):
    """Asientos Contables"""
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    entry_number = db.Column(db.String(20), unique=True, nullable=False)  # Número de asiento
    entry_date = db.Column(db.Date, nullable=False)
    reference = db.Column(db.String(100))  # Referencia externa (factura, recibo, etc.)
    description = db.Column(db.Text, nullable=False)
    period_id = db.Column(db.Integer, db.ForeignKey('accounting_periods.id'))
    status = db.Column(db.String(20), default='DRAFT')  # DRAFT, POSTED, REVERSED
    total_debit = db.Column(db.Numeric(15, 2), default=0)
    total_credit = db.Column(db.Numeric(15, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posted_at = db.Column(db.DateTime)
    
    # Relaciones
    period = db.relationship('AccountingPeriod', backref='journal_entries')
    
    def __repr__(self):
        return f'<JournalEntry {self.entry_number}>'

class JournalEntryDetail(db.Model):
    """Detalles de Asientos Contables - Movimientos por Cuenta"""
    __tablename__ = 'journal_entry_details'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=False)
    third_party_id = db.Column(db.Integer, db.ForeignKey('customers.id'))  # Tercero (cliente/proveedor)
    
    debit_amount = db.Column(db.Numeric(15, 2), default=0)
    credit_amount = db.Column(db.Numeric(15, 2), default=0)
    description = db.Column(db.Text)
    reference = db.Column(db.String(100))  # Documento de cruce
    
    # Relaciones
    journal_entry = db.relationship('JournalEntry', backref='details')
    account = db.relationship('ChartOfAccounts', backref='movements')
    third_party = db.relationship('Customer', backref='accounting_movements')
    
    __table_args__ = (
        Index('idx_journal_detail_entry', 'journal_entry_id'),
        Index('idx_journal_detail_account', 'account_id'),
    )
    
    def __repr__(self):
        return f'<JournalDetail {self.journal_entry.entry_number} - {self.account.code}>'

class AccountBalance(db.Model):
    """Saldos de Cuentas por Periodo"""
    __tablename__ = 'account_balances'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=False)
    period_id = db.Column(db.Integer, db.ForeignKey('accounting_periods.id'), nullable=False)
    
    # Saldos acumulados
    opening_balance = db.Column(db.Numeric(15, 2), default=0)  # Saldo inicial
    debit_total = db.Column(db.Numeric(15, 2), default=0)      # Total débitos
    credit_total = db.Column(db.Numeric(15, 2), default=0)     # Total créditos
    closing_balance = db.Column(db.Numeric(15, 2), default=0)  # Saldo final
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    account = db.relationship('ChartOfAccounts', backref='balances')
    period = db.relationship('AccountingPeriod', backref='account_balances')
    
    __table_args__ = (
        db.UniqueConstraint('account_id', 'period_id'),
        Index('idx_balance_account', 'account_id'),
        Index('idx_balance_period', 'period_id'),
    )
