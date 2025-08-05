from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import login_required, admin_required, get_current_user
from models import User, Warehouse, db
from werkzeug.security import generate_password_hash
from utils.pagination import paginate_query

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@admin_required
def index():
    search = request.args.get('search', '')
    role = request.args.get('role', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%') |
            User.email.ilike(f'%{search}%')
        )
    
    if role:
        query = query.filter_by(role=role)
    
    query = query.order_by(User.username)
    
    users, pagination = paginate_query(query)
    
    return render_template('users/index.html',
                         users=users,
                         pagination=pagination,
                         search=search,
                         role=role)

@users_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def new_user():
    if request.method == 'POST':
        try:
            user = User(
                username=request.form['username'],
                email=request.form['email'],
                password_hash=generate_password_hash(request.form['password']),
                role=request.form['role'],
                warehouse_id=int(request.form['warehouse_id']) if request.form.get('warehouse_id') else None,
                theme=request.form.get('theme', 'blue')
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('users.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear usuario: {str(e)}', 'error')
    
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return render_template('users/form.html', warehouses=warehouses)

@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            user.username = request.form['username']
            user.email = request.form['email']
            user.role = request.form['role']
            user.warehouse_id = int(request.form['warehouse_id']) if request.form.get('warehouse_id') else None
            user.theme = request.form.get('theme', 'blue')
            
            # Update password if provided
            if request.form.get('password'):
                user.password_hash = generate_password_hash(request.form['password'])
            
            db.session.commit()
            
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('users.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar usuario: {str(e)}', 'error')
    
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return render_template('users/form.html', user=user, warehouses=warehouses)

@users_bp.route('/<int:id>/toggle_status', methods=['POST'])
@admin_required
def toggle_status(id):
    user = User.query.get_or_404(id)
    current_user = get_current_user()
    
    # Don't allow deactivating self
    if user.id == current_user.id:
        flash('No puedes desactivar tu propio usuario', 'error')
        return redirect(url_for('users.index'))
    
    user.is_active = not user.is_active
    
    try:
        db.session.commit()
        status = 'activado' if user.is_active else 'desactivado'
        flash(f'Usuario {status} exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return redirect(url_for('users.index'))

@users_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            user.email = request.form['email']
            user.theme = request.form.get('theme', 'blue')
            
            # Update password if provided
            if request.form.get('password'):
                user.password_hash = generate_password_hash(request.form['password'])
            
            db.session.commit()
            
            # Update session theme
            from flask import session
            session['theme'] = user.theme
            
            flash('Perfil actualizado exitosamente', 'success')
            return redirect(url_for('users.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar perfil: {str(e)}', 'error')
    
    return render_template('users/profile.html', user=user)

@users_bp.route('/change_theme', methods=['POST'])
@login_required
def change_theme():
    """AJAX endpoint to change user theme"""
    from flask import session, jsonify
    
    theme = request.form.get('theme', 'blue')
    if theme in ['blue', 'green', 'purple', 'orange']:
        session['theme'] = theme
        
        # Update user's preferred theme in database
        user = get_current_user()
        if user:
            user.theme = theme
            try:
                db.session.commit()
            except:
                db.session.rollback()
        
        return jsonify({'success': True, 'theme': theme})
    
    return jsonify({'success': False, 'error': 'Invalid theme'})
