import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_mail import Mail
from flask_caching import Cache
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
mail = Mail()
cache = Cache()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Database configuration - Using SQLite
    database_path = os.path.join(app.instance_path, 'inventory.db')
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_path}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "connect_args": {"check_same_thread": False}
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Session configuration
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    
    # Mail configuration
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "")
    
    # Cache configuration
    app.config["CACHE_TYPE"] = "simple"
    app.config["CACHE_DEFAULT_TIMEOUT"] = 300
    
    # Initialize extensions
    db.init_app(app)
    Session(app)
    mail.init_app(app)
    cache.init_app(app)
    
    # Register blueprints
    from routes.dashboard import dashboard_bp
    from routes.inventory import inventory_bp
    from routes.sales import sales_bp
    from routes.purchases import purchases_bp
    from routes.pos import pos_bp
    from routes.customers import customers_bp
    from routes.users import users_bp
    from routes.reports import reports_bp
    from routes.settings import settings_bp
    from routes.accounting import accounting_bp
    from auth import auth_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(accounting_bp, url_prefix='/accounting')
    
    with app.app_context():
        # Import models to ensure they're registered
        import models
        db.create_all()
        
        # Create default admin user if none exists
        from werkzeug.security import generate_password_hash
        from datetime import date
        import calendar
        
        if not models.User.query.first():
            admin = models.User(
                username='admin',
                email='admin@empresa.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            
        # Crear datos iniciales del sistema contable
        if not models.ChartOfAccounts.query.first():
            # Plan básico de cuentas contables
            accounts = [
                # ACTIVOS
                {'code': '1', 'name': 'ACTIVOS', 'type': 'ACTIVO', 'level': 1, 'detail': False, 'balance': 'DEBIT'},
                {'code': '1.1', 'name': 'ACTIVO CORRIENTE', 'type': 'ACTIVO', 'level': 2, 'detail': False, 'balance': 'DEBIT', 'parent': '1'},
                {'code': '1.1.01', 'name': 'EFECTIVO Y EQUIVALENTES', 'type': 'ACTIVO', 'level': 3, 'detail': False, 'balance': 'DEBIT', 'parent': '1.1'},
                {'code': '1.1.01.001', 'name': 'Caja General', 'type': 'ACTIVO', 'level': 4, 'detail': True, 'balance': 'DEBIT', 'parent': '1.1.01'},
                {'code': '1.1.01.002', 'name': 'Bancos Cuenta Corriente', 'type': 'ACTIVO', 'level': 4, 'detail': True, 'balance': 'DEBIT', 'parent': '1.1.01'},
                {'code': '1.1.02', 'name': 'CUENTAS POR COBRAR', 'type': 'ACTIVO', 'level': 3, 'detail': False, 'balance': 'DEBIT', 'parent': '1.1'},
                {'code': '1.1.02.001', 'name': 'Clientes Nacionales', 'type': 'ACTIVO', 'level': 4, 'detail': True, 'balance': 'DEBIT', 'parent': '1.1.02'},
                {'code': '1.1.03', 'name': 'INVENTARIOS', 'type': 'ACTIVO', 'level': 3, 'detail': False, 'balance': 'DEBIT', 'parent': '1.1'},
                {'code': '1.1.03.001', 'name': 'Inventario de Mercaderías', 'type': 'ACTIVO', 'level': 4, 'detail': True, 'balance': 'DEBIT', 'parent': '1.1.03'},
                
                # PASIVOS
                {'code': '2', 'name': 'PASIVOS', 'type': 'PASIVO', 'level': 1, 'detail': False, 'balance': 'CREDIT'},
                {'code': '2.1', 'name': 'PASIVO CORRIENTE', 'type': 'PASIVO', 'level': 2, 'detail': False, 'balance': 'CREDIT', 'parent': '2'},
                {'code': '2.1.01', 'name': 'CUENTAS POR PAGAR', 'type': 'PASIVO', 'level': 3, 'detail': False, 'balance': 'CREDIT', 'parent': '2.1'},
                {'code': '2.1.01.001', 'name': 'Proveedores Nacionales', 'type': 'PASIVO', 'level': 4, 'detail': True, 'balance': 'CREDIT', 'parent': '2.1.01'},
                
                # PATRIMONIO
                {'code': '3', 'name': 'PATRIMONIO', 'type': 'PATRIMONIO', 'level': 1, 'detail': False, 'balance': 'CREDIT'},
                {'code': '3.1', 'name': 'CAPITAL', 'type': 'PATRIMONIO', 'level': 2, 'detail': False, 'balance': 'CREDIT', 'parent': '3'},
                {'code': '3.1.01.001', 'name': 'Capital Social', 'type': 'PATRIMONIO', 'level': 4, 'detail': True, 'balance': 'CREDIT', 'parent': '3.1'},
                
                # INGRESOS
                {'code': '4', 'name': 'INGRESOS', 'type': 'INGRESO', 'level': 1, 'detail': False, 'balance': 'CREDIT'},
                {'code': '4.1', 'name': 'INGRESOS OPERACIONALES', 'type': 'INGRESO', 'level': 2, 'detail': False, 'balance': 'CREDIT', 'parent': '4'},
                {'code': '4.1.01.001', 'name': 'Ventas de Mercaderías', 'type': 'INGRESO', 'level': 4, 'detail': True, 'balance': 'CREDIT', 'parent': '4.1'},
                
                # GASTOS
                {'code': '5', 'name': 'GASTOS', 'type': 'GASTO', 'level': 1, 'detail': False, 'balance': 'DEBIT'},
                {'code': '5.1', 'name': 'COSTO DE VENTAS', 'type': 'GASTO', 'level': 2, 'detail': False, 'balance': 'DEBIT', 'parent': '5'},
                {'code': '5.1.01.001', 'name': 'Costo de Mercaderías Vendidas', 'type': 'GASTO', 'level': 4, 'detail': True, 'balance': 'DEBIT', 'parent': '5.1'},
                {'code': '5.2', 'name': 'GASTOS OPERACIONALES', 'type': 'GASTO', 'level': 2, 'detail': False, 'balance': 'DEBIT', 'parent': '5'},
                {'code': '5.2.01.001', 'name': 'Gastos de Administración', 'type': 'GASTO', 'level': 4, 'detail': True, 'balance': 'DEBIT', 'parent': '5.2'},
            ]
            
            # Crear cuentas padre primero
            accounts_map = {}
            for acc_data in accounts:
                if acc_data['level'] == 1:
                    account = models.ChartOfAccounts(
                        code=acc_data['code'],
                        name=acc_data['name'],
                        account_type=acc_data['type'],
                        level=acc_data['level'],
                        is_detail_account=acc_data['detail'],
                        normal_balance=acc_data['balance']
                    )
                    db.session.add(account)
                    db.session.flush()
                    accounts_map[acc_data['code']] = account.id
            
            # Crear cuentas de nivel 2, 3 y 4
            for level in [2, 3, 4]:
                for acc_data in accounts:
                    if acc_data['level'] == level:
                        parent_id = accounts_map.get(acc_data.get('parent'))
                        account = models.ChartOfAccounts(
                            code=acc_data['code'],
                            name=acc_data['name'],
                            account_type=acc_data['type'],
                            level=acc_data['level'],
                            is_detail_account=acc_data['detail'],
                            normal_balance=acc_data['balance'],
                            parent_id=parent_id
                        )
                        db.session.add(account)
                        db.session.flush()
                        accounts_map[acc_data['code']] = account.id
            
            # Crear período contable actual
            current_date = date.today()
            if not models.AccountingPeriod.query.first():
                period = models.AccountingPeriod(
                    name=f"{calendar.month_name[current_date.month]} {current_date.year}",
                    year=current_date.year,
                    month=current_date.month,
                    start_date=date(current_date.year, current_date.month, 1),
                    end_date=date(current_date.year, current_date.month, calendar.monthrange(current_date.year, current_date.month)[1])
                )
                db.session.add(period)
            
            db.session.commit()
    
    return app

app = create_app()
