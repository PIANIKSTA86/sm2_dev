from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import (db, ChartOfAccounts, AccountingPeriod, JournalEntry, JournalEntryDetail, 
                   Customer, Setting)
from utils.pagination import paginate_query
from sqlalchemy import text, desc, and_, or_
from datetime import datetime, date
from decimal import Decimal
import logging

accounting_bp = Blueprint('accounting', __name__)

@accounting_bp.route('/')
@login_required
def index():
    """Dashboard principal de contabilidad"""
    # Obtener período contable actual
    current_period = AccountingPeriod.query.filter_by(is_closed=False).order_by(desc(AccountingPeriod.start_date)).first()
    
    # Estadísticas básicas
    stats = {
        'total_accounts': ChartOfAccounts.query.filter_by(is_active=True).count(),
        'journal_entries': JournalEntry.query.count(),
        'current_period': current_period.name if current_period else 'Sin período activo',
        'open_periods': AccountingPeriod.query.filter_by(is_closed=False).count()
    }
    
    # Últimos asientos contables
    recent_entries = JournalEntry.query.order_by(desc(JournalEntry.created_at)).limit(10).all()
    
    return render_template('accounting/dashboard.html', 
                         stats=stats, 
                         recent_entries=recent_entries,
                         current_period=current_period)

@accounting_bp.route('/chart_of_accounts')
@login_required
def chart_of_accounts():
    """Plan de cuentas contables"""
    search = request.args.get('search', '')
    account_type = request.args.get('account_type', '')
    
    query = ChartOfAccounts.query
    
    if search:
        query = query.filter(or_(
            ChartOfAccounts.code.contains(search),
            ChartOfAccounts.name.contains(search)
        ))
    
    if account_type:
        query = query.filter(ChartOfAccounts.account_type == account_type)
    
    query = query.order_by(ChartOfAccounts.code)
    pagination = paginate_query(query, request.args.get('page', 1, type=int))
    
    # Tipos de cuenta para filtro
    account_types = db.session.query(ChartOfAccounts.account_type.distinct()).all()
    account_types = [t[0] for t in account_types]
    
    return render_template('accounting/chart_of_accounts.html',
                         accounts=pagination.items,
                         pagination=pagination,
                         search=search,
                         account_type=account_type,
                         account_types=account_types)

@accounting_bp.route('/chart_of_accounts/new', methods=['GET', 'POST'])
@login_required
def add_account():
    """Agregar nueva cuenta contable"""
    if request.method == 'POST':
        try:
            account = ChartOfAccounts(
                code=request.form['code'],
                name=request.form['name'],
                description=request.form.get('description', ''),
                account_type=request.form['account_type'],
                account_subtype=request.form.get('account_subtype', ''),
                parent_id=request.form.get('parent_id') if request.form.get('parent_id') else None,
                level=int(request.form.get('level', 1)),
                is_detail_account=request.form.get('is_detail_account') == 'on',
                normal_balance=request.form['normal_balance'],
                is_active=True
            )
            
            db.session.add(account)
            db.session.commit()
            flash('Cuenta contable creada exitosamente', 'success')
            return redirect(url_for('accounting.chart_of_accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear cuenta: {str(e)}', 'error')
    
    # Obtener cuentas padre para el select
    parent_accounts = ChartOfAccounts.query.filter_by(is_active=True).order_by(ChartOfAccounts.code).all()
    
    return render_template('accounting/add_account.html', parent_accounts=parent_accounts)

@accounting_bp.route('/periods')
@login_required
def periods():
    """Gestión de períodos contables"""
    periods = AccountingPeriod.query.order_by(desc(AccountingPeriod.year), desc(AccountingPeriod.month)).all()
    return render_template('accounting/periods.html', periods=periods)

@accounting_bp.route('/periods/new', methods=['GET', 'POST'])
@login_required
def create_period():
    """Crear nuevo período contable"""
    if request.method == 'POST':
        try:
            period = AccountingPeriod(
                name=request.form['name'],
                year=int(request.form['year']),
                month=int(request.form['month']),
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
                is_closed=False
            )
            
            db.session.add(period)
            db.session.commit()
            flash('Período contable creado exitosamente', 'success')
            return redirect(url_for('accounting.periods'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear período: {str(e)}', 'error')
    
    return render_template('accounting/create_period.html')

@accounting_bp.route('/journal_entries')
@login_required
def journal_entries():
    """Listado de asientos contables"""
    search = request.args.get('search', '')
    period_id = request.args.get('period_id', '')
    
    query = JournalEntry.query
    
    if search:
        query = query.filter(or_(
            JournalEntry.entry_number.contains(search),
            JournalEntry.reference.contains(search),
            JournalEntry.description.contains(search)
        ))
    
    if period_id:
        period = AccountingPeriod.query.get(period_id)
        if period:
            query = query.filter(and_(
                JournalEntry.entry_date >= period.start_date,
                JournalEntry.entry_date <= period.end_date
            ))
    
    query = query.order_by(desc(JournalEntry.entry_date), desc(JournalEntry.entry_number))
    pagination = paginate_query(query, request.args.get('page', 1, type=int))
    
    # Períodos para filtro
    periods = AccountingPeriod.query.order_by(desc(AccountingPeriod.year), desc(AccountingPeriod.month)).all()
    
    return render_template('accounting/journal_entries.html',
                         entries=pagination.items,
                         pagination=pagination,
                         search=search,
                         period_id=period_id,
                         periods=periods)

@accounting_bp.route('/journal_entries/new', methods=['GET', 'POST'])
@login_required
def add_journal_entry():
    """Crear nuevo asiento contable por partida doble"""
    if request.method == 'POST':
        try:
            # Generar número de asiento automático
            last_entry = JournalEntry.query.order_by(desc(JournalEntry.id)).first()
            entry_number = f"AST-{(last_entry.id + 1) if last_entry else 1:06d}"
            
            # Crear asiento principal
            entry = JournalEntry(
                entry_number=entry_number,
                entry_date=datetime.strptime(request.form['entry_date'], '%Y-%m-%d').date(),
                reference=request.form.get('reference', ''),
                description=request.form['description'],
                period_id=request.form.get('period_id') if request.form.get('period_id') else None,
                created_by=current_user.id,
                total_debit=Decimal('0'),
                total_credit=Decimal('0')
            )
            
            db.session.add(entry)
            db.session.flush()  # Para obtener el ID del asiento
            
            # Procesar detalles del asiento (partida doble)
            total_debit = Decimal('0')
            total_credit = Decimal('0')
            
            # Obtener datos de débitos y créditos del formulario
            debit_accounts = request.form.getlist('debit_account_id')
            debit_amounts = request.form.getlist('debit_amount')
            debit_descriptions = request.form.getlist('debit_description')
            debit_third_parties = request.form.getlist('debit_third_party_id')
            debit_references = request.form.getlist('debit_reference')
            
            credit_accounts = request.form.getlist('credit_account_id')
            credit_amounts = request.form.getlist('credit_amount')
            credit_descriptions = request.form.getlist('credit_description')
            credit_third_parties = request.form.getlist('credit_third_party_id')
            credit_references = request.form.getlist('credit_reference')
            
            # Procesar débitos
            for i, account_id in enumerate(debit_accounts):
                if account_id and i < len(debit_amounts) and debit_amounts[i]:
                    amount = Decimal(debit_amounts[i])
                    detail = JournalEntryDetail(
                        journal_entry_id=entry.id,
                        account_id=int(account_id),
                        debit_amount=amount,
                        credit_amount=Decimal('0'),
                        description=debit_descriptions[i] if i < len(debit_descriptions) else '',
                        third_party_id=int(debit_third_parties[i]) if i < len(debit_third_parties) and debit_third_parties[i] else None,
                        reference=debit_references[i] if i < len(debit_references) else ''
                    )
                    db.session.add(detail)
                    total_debit += amount
            
            # Procesar créditos
            for i, account_id in enumerate(credit_accounts):
                if account_id and i < len(credit_amounts) and credit_amounts[i]:
                    amount = Decimal(credit_amounts[i])
                    detail = JournalEntryDetail(
                        journal_entry_id=entry.id,
                        account_id=int(account_id),
                        debit_amount=Decimal('0'),
                        credit_amount=amount,
                        description=credit_descriptions[i] if i < len(credit_descriptions) else '',
                        third_party_id=int(credit_third_parties[i]) if i < len(credit_third_parties) and credit_third_parties[i] else None,
                        reference=credit_references[i] if i < len(credit_references) else ''
                    )
                    db.session.add(detail)
                    total_credit += amount
            
            # Validar partida doble (débitos = créditos)
            if total_debit != total_credit:
                raise ValueError(f'El asiento no está balanceado. Débitos: {total_debit}, Créditos: {total_credit}')
            
            # Actualizar totales del asiento
            entry.total_debit = total_debit
            entry.total_credit = total_credit
            
            db.session.commit()
            flash('Asiento contable creado exitosamente', 'success')
            return redirect(url_for('accounting.journal_entries'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear asiento: {str(e)}', 'error')
    
    # Obtener datos para el formulario
    accounts = ChartOfAccounts.query.filter_by(is_active=True, is_detail_account=True).order_by(ChartOfAccounts.code).all()
    third_parties = Customer.query.filter_by(is_active=True).order_by(Customer.first_name, Customer.last_name).all()
    periods = AccountingPeriod.query.filter_by(is_closed=False).order_by(desc(AccountingPeriod.year), desc(AccountingPeriod.month)).all()
    
    return render_template('accounting/add_journal_entry.html',
                         accounts=accounts,
                         third_parties=third_parties,
                         periods=periods)

@accounting_bp.route('/journal_entries/<int:id>')
@login_required
def view_journal_entry(id):
    """Ver detalle de asiento contable"""
    entry = JournalEntry.query.get_or_404(id)
    return render_template('accounting/view_journal_entry.html', entry=entry)

@accounting_bp.route('/trial_balance')
@login_required
def trial_balance():
    """Balance de comprobación"""
    period_id = request.args.get('period_id', '')
    
    # Si no hay período seleccionado, usar el más reciente
    if not period_id:
        period = AccountingPeriod.query.order_by(desc(AccountingPeriod.year), desc(AccountingPeriod.month)).first()
        if period:
            period_id = str(period.id)
    
    # Consulta para balance de comprobación
    trial_balance_data = []
    
    if period_id:
        period = AccountingPeriod.query.get(period_id)
        if period:
            # Obtener balances por cuenta
            query = db.session.query(
                ChartOfAccounts.code,
                ChartOfAccounts.name,
                ChartOfAccounts.account_type,
                ChartOfAccounts.normal_balance,
                db.func.sum(JournalEntryDetail.debit_amount).label('total_debit'),
                db.func.sum(JournalEntryDetail.credit_amount).label('total_credit')
            ).join(JournalEntryDetail).join(JournalEntry)\
            .filter(and_(
                JournalEntry.entry_date >= period.start_date,
                JournalEntry.entry_date <= period.end_date,
                ChartOfAccounts.is_active == True
            ))\
            .group_by(ChartOfAccounts.id)\
            .order_by(ChartOfAccounts.code)
            
            results = query.all()
            
            for row in results:
                total_debit = row.total_debit or Decimal('0')
                total_credit = row.total_credit or Decimal('0')
                balance = total_debit - total_credit
                
                trial_balance_data.append({
                    'code': row.code,
                    'name': row.name,
                    'account_type': row.account_type,
                    'normal_balance': row.normal_balance,
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'balance': balance
                })
    
    # Períodos disponibles
    periods = AccountingPeriod.query.order_by(desc(AccountingPeriod.year), desc(AccountingPeriod.month)).all()
    
    return render_template('accounting/trial_balance.html',
                         trial_balance_data=trial_balance_data,
                         periods=periods,
                         selected_period_id=period_id)

@accounting_bp.route('/api/accounts/search')
@login_required
def api_search_accounts():
    """API para búsqueda de cuentas contables"""
    q = request.args.get('q', '')
    accounts = ChartOfAccounts.query.filter(
        and_(
            ChartOfAccounts.is_active == True,
            ChartOfAccounts.is_detail_account == True,
            or_(
                ChartOfAccounts.code.contains(q),
                ChartOfAccounts.name.contains(q)
            )
        )
    ).limit(20).all()
    
    return jsonify([{
        'id': account.id,
        'code': account.code,
        'name': account.name,
        'display': f"{account.code} - {account.name}"
    } for account in accounts])

@accounting_bp.route('/api/third_parties/search')
@login_required
def api_search_third_parties():
    """API para búsqueda de terceros"""
    q = request.args.get('q', '')
    third_parties = Customer.query.filter(
        and_(
            Customer.is_active == True,
            or_(
                Customer.first_name.contains(q),
                Customer.last_name.contains(q),
                Customer.document_number.contains(q)
            )
        )
    ).limit(20).all()
    
    return jsonify([{
        'id': party.id,
        'name': f"{party.first_name} {party.last_name}",
        'document': party.document_number,
        'display': f"{party.first_name} {party.last_name} ({party.document_number})"
    } for party in third_parties])