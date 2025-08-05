from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from flask import make_response
from models import Setting
import io
from datetime import datetime

def get_company_info():
    """Get company information from settings"""
    from app import db
    
    settings = db.session.query(Setting).filter_by(category='company').all()
    company_info = {setting.key: setting.value for setting in settings}
    
    return {
        'name': company_info.get('company_name', 'Mi Empresa'),
        'address': company_info.get('company_address', ''),
        'phone': company_info.get('company_phone', ''),
        'email': company_info.get('company_email', ''),
        'tax_id': company_info.get('company_tax_id', ''),
        'currency_symbol': company_info.get('currency_symbol', '$'),
        'footer': company_info.get('invoice_footer', 'Gracias por su compra')
    }

def generate_invoice_pdf(sale, download=False):
    """Generate PDF invoice for a sale"""
    
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                          rightMargin=2*cm, leftMargin=2*cm,
                          topMargin=2*cm, bottomMargin=2*cm)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    normal_style = styles['Normal']
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold'
    )
    
    # Get company info
    company_info = get_company_info()
    
    # Header - Company info
    elements.append(Paragraph(company_info['name'], title_style))
    
    if company_info['address']:
        elements.append(Paragraph(company_info['address'], normal_style))
    
    contact_info = []
    if company_info['phone']:
        contact_info.append(f"Tel: {company_info['phone']}")
    if company_info['email']:
        contact_info.append(f"Email: {company_info['email']}")
    if company_info['tax_id']:
        contact_info.append(f"NIT: {company_info['tax_id']}")
    
    if contact_info:
        elements.append(Paragraph(" | ".join(contact_info), normal_style))
    
    elements.append(Spacer(1, 20))
    
    # Invoice header
    invoice_header = [
        [Paragraph('<b>FACTURA DE VENTA</b>', bold_style), ''],
        [f'Número: {sale.invoice_number}', f'Fecha: {sale.created_at.strftime("%d/%m/%Y %H:%M")}'],
        [f'Bodega: {sale.warehouse.name}', f'Vendedor: {sale.user.username}']
    ]
    
    if sale.customer:
        invoice_header.extend([
            ['', ''],
            [Paragraph('<b>DATOS DEL CLIENTE</b>', bold_style), ''],
            [f'Cliente: {sale.customer.name}', ''],
        ])
        
        if sale.customer.document_number:
            invoice_header.append([f'Documento: {sale.customer.document_number}', ''])
        if sale.customer.email:
            invoice_header.append([f'Email: {sale.customer.email}', ''])
        if sale.customer.phone:
            invoice_header.append([f'Teléfono: {sale.customer.phone}', ''])
        if sale.customer.address:
            invoice_header.append([f'Dirección: {sale.customer.address}', ''])
    
    header_table = Table(invoice_header, colWidths=[3*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 20))
    
    # Invoice details table
    data = [['Producto', 'Cant.', 'Precio Unit.', 'Desc.', 'Total']]
    
    currency_symbol = company_info['currency_symbol']
    
    for detail in sale.details:
        product_name = detail.product.name
        if detail.serial and detail.serial.serial_imei:
            product_name += f"\nS/N: {detail.serial.serial_imei}"
        
        discount_text = f"{detail.discount_percent}%" if detail.discount_percent > 0 else "-"
        
        data.append([
            product_name,
            f"{detail.quantity:,.2f}",
            f"{currency_symbol}{detail.unit_price:,.2f}",
            discount_text,
            f"{currency_symbol}{detail.total:,.2f}"
        ])
    
    details_table = Table(data, colWidths=[3*inch, 0.8*inch, 1*inch, 0.7*inch, 1*inch])
    details_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        
        # Data rows
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    elements.append(details_table)
    elements.append(Spacer(1, 20))
    
    # Totals
    totals_data = [
        ['Subtotal:', f"{currency_symbol}{sale.subtotal:,.2f}"],
    ]
    
    if sale.discount_amount > 0:
        totals_data.append(['Descuento:', f"-{currency_symbol}{sale.discount_amount:,.2f}"])
    
    if sale.tax_amount > 0:
        totals_data.append(['Impuesto:', f"{currency_symbol}{sale.tax_amount:,.2f}"])
    
    totals_data.append(['TOTAL:', f"{currency_symbol}{sale.total:,.2f}"])
    
    totals_table = Table(totals_data, colWidths=[2*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
    ]))
    
    # Right align totals table
    totals_wrapper = Table([[totals_table]], colWidths=[6*inch])
    totals_wrapper.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
    ]))
    
    elements.append(totals_wrapper)
    elements.append(Spacer(1, 30))
    
    # Payment method
    if sale.payment_method:
        payment_text = f"Método de pago: {sale.payment_method.upper()}"
        elements.append(Paragraph(payment_text, normal_style))
    
    # Notes
    if sale.notes:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Notas: {sale.notes}", normal_style))
    
    # Footer
    elements.append(Spacer(1, 30))
    if company_info['footer']:
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=8
        )
        elements.append(Paragraph(company_info['footer'], footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and create response
    pdf_data = buffer.getvalue()
    buffer.close()
    
    if download:
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=factura_{sale.invoice_number}.pdf'
        return response
    
    return pdf_data
