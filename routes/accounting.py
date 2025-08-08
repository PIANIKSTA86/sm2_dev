from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db, cache
from models import (
    ChartOfAccounts, AccountingPeriod, JournalEntry, JournalEntryDetail, 
    AccountBalance, User
)
from datetime import datetime, date
from sqlalchemy import func, and_, or_, desc, asc
from decimal import Decimal
import calendar

accounting_bp = Blueprint('accounting', __name__)

@accounting_bp.route('/')
def dashboard():
    """Dashboard principal del módulo contable"""
    # Obtener el periodo actual
    current_date = datetime.now()
    current_period = AccountingPeriod.query.filter(
        and_(
            AccountingPeriod.year == current_date.year,
            AccountingPeriod.month == current_date.month
        )
    ).first()
    
    # Estadísticas básicas
    stats = {
        'total_accounts': ChartOfAccounts.query.filter_by(is_active=True).count(),
        'current_period': current_period.name if current_period else 'Sin período',
        'pending_entries': JournalEntry.query.filter_by(status='DRAFT').count(),
        'posted_entries': JournalEntry.query.filter_by(status='POSTED').count()
    }
    
    # Últimos asientos contables
    recent_entries = JournalEntry.query.order_by(desc(JournalEntry.created_at)).limit(5).all()
    
    return render_template('accounting/dashboard.html', 
                         stats=stats, 
                         recent_entries=recent_entries,
                         current_period=current_period)

@accounting_bp.route('/chart-of-accounts')
def chart_of_accounts():
    """Plan de cuentas"""
    search = request.args.get('search', '')
    account_type = request.args.get('type', '')
    
    query = ChartOfAccounts.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(or_(
            ChartOfAccounts.code.contains(search),
            ChartOfAccounts.name.contains(search)
        ))
    
    if account_type:
        query = query.filter_by(account_type=account_type)
    
    accounts = query.order_by(ChartOfAccounts.code).all()
    
    # Tipos de cuenta disponibles
    account_types = ['ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO']
    
    return render_template('accounting/chart_of_accounts.html', 
                         accounts=accounts, 
                         account_types=account_types,
                         search=search,
                         selected_type=account_type)

@accounting_bp.route('/chart-of-accounts/add', methods=['GET', 'POST'])
def add_account():
    """Agregar nueva cuenta contable"""
    if request.method == 'POST':
        try:
            account = ChartOfAccounts(
                code=request.form['code'].strip(),
                name=request.form['name'].strip(),
                description=request.form.get('description', '').strip(),
                account_type=request.form['account_type'],
                account_subtype=request.form.get('account_subtype', '').strip(),
                parent_id=request.form.get('parent_id') or None,
                level=int(request.form.get('level', 1)),
                is_detail_account=bool(request.form.get('is_detail_account')),
                normal_balance=request.form['normal_balance']
            )
            
            db.session.add(account)
            db.session.commit()
            flash('Cuenta contable creada exitosamente', 'success')
            return redirect(url_for('accounting.chart_of_accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la cuenta: {str(e)}', 'error')
    
    # Para el formulario, obtener cuentas padre
    parent_accounts = ChartOfAccounts.query.filter_by(
        is_active=True, 
        is_detail_account=False
    ).order_by(ChartOfAccounts.code).all()
    
    return render_template('accounting/add_account.html', 
                         parent_accounts=parent_accounts)

@accounting_bp.route('/periods')
def periods():
    """Gestión de períodos contables"""
    periods = AccountingPeriod.query.order_by(
        desc(AccountingPeriod.year), 
        desc(AccountingPeriod.month)
    ).all()
    
    return render_template('accounting/periods.html', periods=periods)

@accounting_bp.route('/periods/create', methods=['GET', 'POST'])
def create_period():
    """Crear nuevo período contable"""
    if request.method == 'POST':
        try:
            year = int(request.form['year'])
            month = int(request.form['month'])
            
            # Calcular fechas del período
            start_date = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)
            
            period = AccountingPeriod(
                name=f"{calendar.month_name[month]} {year}",
                year=year,
                month=month,
                start_date=start_date,
                end_date=end_date
            )
            
            db.session.add(period)
            db.session.commit()
            flash('Período contable creado exitosamente', 'success')
            return redirect(url_for('accounting.periods'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el período: {str(e)}', 'error')
    
    return render_template('accounting/create_period.html')

@accounting_bp.route('/journal-entries')
def journal_entries():
    """Lista de asientos contables"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = JournalEntry.query
    
    if status:
        query = query.filter_by(status=status)
    
    if date_from:
        query = query.filter(JournalEntry.entry_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(JournalEntry.entry_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    entries = query.order_by(desc(JournalEntry.entry_date)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('accounting/journal_entries.html', 
                         entries=entries,
                         status=status,
                         date_from=date_from,
                         date_to=date_to)

@accounting_bp.route('/journal-entries/add', methods=['GET', 'POST'])
def add_journal_entry():
    """Crear nuevo asiento contable"""
    if request.method == 'POST':
        try:
            # Validar que las sumas de débitos y créditos sean iguales
            total_debit = Decimal('0')
            total_credit = Decimal('0')
            
            # Procesar las líneas del asiento
            details = []
            for i in range(len(request.form.getlist('account_id'))):
                account_id = request.form.getlist('account_id')[i]
                debit = Decimal(request.form.getlist('debit')[i] or '0')
                credit = Decimal(request.form.getlist('credit')[i] or '0')
                
                if account_id and (debit > 0 or credit > 0):
                    details.append({
                        'account_id': int(account_id),
                        'debit_amount': debit,
                        'credit_amount': credit,
                        'description': request.form.getlist('line_description')[i],
                        'line_number': i + 1
                    })
                    total_debit += debit
                    total_credit += credit
            
            # Validar partida doble
            if total_debit != total_credit:
                flash('Error: La suma de débitos debe ser igual a la suma de créditos', 'error')
                raise ValueError("Partida doble no balanceada")
            
            if not details:
                flash('Error: Debe agregar al menos una línea al asiento', 'error')
                raise ValueError("Sin líneas de detalle")
            
            # Generar número de asiento
            entry_number = f"AST-{datetime.now().strftime('%Y%m%d')}-{JournalEntry.query.count() + 1:04d}"
            
            # Crear el asiento
            entry = JournalEntry(
                entry_number=entry_number,
                entry_date=datetime.strptime(request.form['entry_date'], '%Y-%m-%d').date(),
                reference=request.form.get('reference', ''),
                description=request.form['description'],
                period_id=int(request.form['period_id']),
                user_id=current_user.id,
                total_debit=total_debit,
                total_credit=total_credit,
                source_module='MANUAL'
            )
            
            db.session.add(entry)
            db.session.flush()  # Para obtener el ID
            
            # Crear las líneas de detalle
            for detail_data in details:
                detail = JournalEntryDetail(
                    journal_entry_id=entry.id,
                    **detail_data
                )
                db.session.add(detail)
            
            db.session.commit()
            flash('Asiento contable creado exitosamente', 'success')
            return redirect(url_for('accounting.journal_entries'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el asiento: {str(e)}', 'error')
    
    # Para el formulario
    accounts = ChartOfAccounts.query.filter_by(
        is_active=True, 
        is_detail_account=True
    ).order_by(ChartOfAccounts.code).all()
    
    periods = AccountingPeriod.query.filter_by(is_closed=False).order_by(
        desc(AccountingPeriod.year), 
        desc(AccountingPeriod.month)
    ).all()
    
    return render_template('accounting/add_journal_entry.html', 
                         accounts=accounts, 
                         periods=periods)

@accounting_bp.route('/journal-entries/<int:entry_id>/post', methods=['POST'])
def post_journal_entry(entry_id):
    """Contabilizar un asiento (cambiar estado de DRAFT a POSTED)"""
    try:
        entry = JournalEntry.query.get_or_404(entry_id)
        
        if entry.status != 'DRAFT':
            flash('Solo se pueden contabilizar asientos en estado borrador', 'error')
            return redirect(url_for('accounting.journal_entries'))
        
        entry.status = 'POSTED'
        entry.posted_at = datetime.utcnow()
        
        # Actualizar saldos de cuentas
        for detail in entry.details:
            balance = AccountBalance.query.filter_by(
                account_id=detail.account_id,
                period_id=entry.period_id
            ).first()
            
            if not balance:
                balance = AccountBalance(
                    account_id=detail.account_id,
                    period_id=entry.period_id
                )
                db.session.add(balance)
            
            balance.debit_total += detail.debit_amount
            balance.credit_total += detail.credit_amount
            
            # Calcular saldo final según el tipo de cuenta
            account = detail.account
            if account.normal_balance == 'DEBIT':
                balance.closing_balance = (balance.opening_balance + 
                                         balance.debit_total - balance.credit_total)
            else:
                balance.closing_balance = (balance.opening_balance + 
                                         balance.credit_total - balance.debit_total)
            
            balance.last_updated = datetime.utcnow()
        
        db.session.commit()
        flash('Asiento contabilizado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al contabilizar el asiento: {str(e)}', 'error')
    
    return redirect(url_for('accounting.journal_entries'))

@accounting_bp.route('/reports/trial-balance')
def trial_balance():
    """Reporte de Balance de Comprobación"""
    period_id = request.args.get('period_id', type=int)
    
    if period_id:
        period = AccountingPeriod.query.get_or_404(period_id)
        
        # Obtener saldos de todas las cuentas para el período
        balances = db.session.query(
            AccountBalance,
            ChartOfAccounts
        ).join(
            ChartOfAccounts
        ).filter(
            AccountBalance.period_id == period_id
        ).order_by(
            ChartOfAccounts.code
        ).all()
        
        # Calcular totales
        total_debit = sum(b.AccountBalance.debit_total for b in balances)
        total_credit = sum(b.AccountBalance.credit_total for b in balances)
        
        return render_template('accounting/trial_balance.html',
                             balances=balances,
                             period=period,
                             total_debit=total_debit,
                             total_credit=total_credit)
    
    # Mostrar selector de período
    periods = AccountingPeriod.query.order_by(
        desc(AccountingPeriod.year), 
        desc(AccountingPeriod.month)
    ).all()
    
    return render_template('accounting/select_period.html', 
                         periods=periods, 
                         report_type='trial_balance')

# API endpoints para AJAX
@accounting_bp.route('/api/accounts')
def api_accounts():
    """API para obtener cuentas contables (para autocomplete)"""
    search = request.args.get('q', '')
    
    query = ChartOfAccounts.query.filter(
        ChartOfAccounts.is_active == True,
        ChartOfAccounts.is_detail_account == True
    )
    
    if search:
        query = query.filter(or_(
            ChartOfAccounts.code.contains(search),
            ChartOfAccounts.name.contains(search)
        ))
    
    accounts = query.limit(10).all()
    
    return jsonify([{
        'id': acc.id,
        'code': acc.code,
        'name': acc.name,
        'normal_balance': acc.normal_balance
    } for acc in accounts])

@accounting_bp.route('/api/accounts/<int:account_id>/balance')
def api_account_balance(account_id):
    """API para obtener el saldo actual de una cuenta"""
    period_id = request.args.get('period_id', type=int)
    
    if period_id:
        balance = AccountBalance.query.filter_by(
            account_id=account_id,
            period_id=period_id
        ).first()
        
        if balance:
            return jsonify({
                'closing_balance': float(balance.closing_balance),
                'debit_total': float(balance.debit_total),
                'credit_total': float(balance.credit_total)
            })
    
    return jsonify({
        'closing_balance': 0,
        'debit_total': 0,
        'credit_total': 0
    })