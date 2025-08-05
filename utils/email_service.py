from flask_mail import Message
from app import mail
from flask import current_app
import os

def send_invoice_email(to_email, sale, pdf_data):
    """Send invoice via email"""
    
    try:
        msg = Message(
            subject=f'Factura {sale.invoice_number}',
            recipients=[to_email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        # Email body
        customer_name = sale.customer.name if sale.customer else 'Estimado cliente'
        
        msg.html = f"""
        <html>
        <body>
            <h2>Factura de Venta</h2>
            <p>Hola {customer_name},</p>
            
            <p>Se adjunta la factura de su compra:</p>
            
            <ul>
                <li><strong>Número de factura:</strong> {sale.invoice_number}</li>
                <li><strong>Fecha:</strong> {sale.created_at.strftime('%d/%m/%Y %H:%M')}</li>
                <li><strong>Total:</strong> ${sale.total:,.2f}</li>
            </ul>
            
            <p>Gracias por su compra.</p>
            
            <p>Saludos cordiales,<br>
            Equipo de Ventas</p>
        </body>
        </html>
        """
        
        # Attach PDF
        msg.attach(
            filename=f'factura_{sale.invoice_number}.pdf',
            content_type='application/pdf',
            data=pdf_data
        )
        
        mail.send(msg)
        return True
        
    except Exception as e:
        current_app.logger.error(f'Error sending email: {str(e)}')
        raise e

def send_notification_email(to_email, subject, message):
    """Send general notification email"""
    
    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        msg.body = message
        
        mail.send(msg)
        return True
        
    except Exception as e:
        current_app.logger.error(f'Error sending notification email: {str(e)}')
        raise e

def send_low_stock_alert(products):
    """Send low stock alert to admin users"""
    
    from models import User
    
    admin_users = User.query.filter_by(role='admin', is_active=True).all()
    admin_emails = [user.email for user in admin_users if user.email]
    
    if not admin_emails or not products:
        return
    
    # Build message
    product_list = "\n".join([
        f"- {p.name} (SKU: {p.sku}): {p.quantity} unidades"
        for p in products
    ])
    
    message = f"""
    Alerta de Stock Bajo
    
    Los siguientes productos tienen stock bajo:
    
    {product_list}
    
    Por favor, revise el inventario y realice las compras necesarias.
    
    Sistema de Inventario
    """
    
    try:
        for email in admin_emails:
            send_notification_email(email, "Alerta de Stock Bajo", message)
    except Exception as e:
        current_app.logger.error(f'Error sending low stock alert: {str(e)}')
