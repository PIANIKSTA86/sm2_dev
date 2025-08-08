import json
import os
from datetime import datetime
from models import *
from app import db
from flask import current_app

def create_backup():
    """Create a JSON backup of the database"""
    
    try:
        backup_data = {
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
            'data': {}
        }
        
        # Define tables to backup (excluding sensitive user data)
        tables_to_backup = [
            ('warehouses', Warehouse),
            ('categories', Category),
            ('brands', Brand),
            ('product_groups', ProductGroup),
            ('product_lines', ProductLine),
            ('products', Product),
            ('inventory', Inventory),
            ('customers', Customer),
            ('sales', Sale),
            ('sale_details', SaleDetail),
            ('purchases', Purchase),
            ('purchase_details', PurchaseDetail),
            ('serial_numbers', SerialNumber),
            ('settings', Setting)
        ]
        
        for table_name, model_class in tables_to_backup:
            records = model_class.query.all()
            backup_data['data'][table_name] = []
            
            for record in records:
                record_dict = {}
                for column in model_class.__table__.columns:
                    value = getattr(record, column.name)
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    elif hasattr(value, '__float__'):
                        value = float(value)
                    record_dict[column.name] = value
                
                backup_data['data'][table_name].append(record_dict)
        
        # Create backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.json'
        backup_path = f'/tmp/{backup_filename}'
        
        # Write backup file
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        current_app.logger.info(f'Backup created: {backup_filename}')
        return backup_filename
        
    except Exception as e:
        current_app.logger.error(f'Error creating backup: {str(e)}')
        raise e

def restore_backup(backup_file_path):
    """Restore database from JSON backup"""
    
    try:
        with open(backup_file_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        if 'data' not in backup_data:
            raise ValueError('Invalid backup file format')
        
        # Clear existing data (be careful!)
        # This is a simplified version - in production, you'd want more sophisticated handling
        # PostgreSQL doesn't use SET foreign_key_checks, we'll handle this differently
        pass
        
        # Define restore order (considering foreign key dependencies)
        restore_order = [
            ('settings', Setting),
            ('warehouses', Warehouse),
            ('categories', Category),
            ('brands', Brand),
            ('product_groups', ProductGroup),
            ('product_lines', ProductLine),
            ('products', Product),
            ('inventory', Inventory),
            ('customers', Customer),
            ('serial_numbers', SerialNumber),
            ('sales', Sale),
            ('sale_details', SaleDetail),
            ('purchases', Purchase),
            ('purchase_details', PurchaseDetail)
        ]
        
        for table_name, model_class in restore_order:
            if table_name in backup_data['data']:
                # Clear existing records
                model_class.query.delete()
                
                # Insert backup records
                for record_data in backup_data['data'][table_name]:
                    # Convert datetime strings back to datetime objects
                    for key, value in record_data.items():
                        if key.endswith('_at') and isinstance(value, str):
                            try:
                                record_data[key] = datetime.fromisoformat(value)
                            except:
                                pass
                    
                    # Create new record
                    record = model_class(**record_data)
                    db.session.add(record)
                
                db.session.flush()
        
        # Foreign key constraints re-enabled automatically in PostgreSQL
        db.session.commit()
        
        current_app.logger.info(f'Backup restored from: {backup_file_path}')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error restoring backup: {str(e)}')
        raise e

def schedule_automatic_backup():
    """Schedule automatic backups (would need a task scheduler in production)"""
    
    # This is a placeholder for automatic backup scheduling
    # In production, you'd use Celery, cron jobs, or similar
    pass

def cleanup_old_backups(keep_days=30):
    """Clean up old backup files"""
    
    backup_dir = '/tmp'
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    try:
        for filename in os.listdir(backup_dir):
            if filename.startswith('backup_') and filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                file_date = datetime.fromtimestamp(os.path.getctime(filepath))
                
                if file_date < cutoff_date:
                    os.remove(filepath)
                    current_app.logger.info(f'Deleted old backup: {filename}')
                    
    except Exception as e:
        current_app.logger.error(f'Error cleaning up backups: {str(e)}')
