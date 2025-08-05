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

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # client, supplier, employee, other
    document_type = db.Column(db.String(20))  # cedula, nit, passport
    document_number = db.Column(db.String(50))
    name = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    credit_limit = db.Column(db.Numeric(12, 2), default=0)
    credit_days = db.Column(db.Integer, default=0)
    price_level = db.Column(db.Integer, default=1)  # 1-4 para price1-4
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_customer_search', 'name', 'document_number', 'email'),
        Index('idx_customer_type', 'type'),
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

class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
