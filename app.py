# app.py
# Main Flask application file for the collaborative scenario writer (Arabic Version).

import os
import io
import json
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, session, abort, current_app, send_file)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# Import models including Maslak and Status Constants
from models import (db, User, Episode, Assignment, Comment, Maslak, AuditLog, # <<< Added AuditLog
                    EPISODE_STATUS_DRAFT, EPISODE_STATUS_REVIEW, EPISODE_STATUS_COMPLETE,
                    EPISODE_STATUS_CHOICES)
from dotenv import load_dotenv
from sqlalchemy.orm import joinedload, subqueryload
from werkzeug.security import generate_password_hash, check_password_hash
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
# Updated WTForms imports
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, EqualTo, Length, Optional
import markdown
from weasyprint import HTML, CSS
from flask_migrate import Migrate # Keep Migrate import

# Load environment variables
load_dotenv()

# --- App Initialization & Config ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key_arabic')
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
db_dir = os.path.dirname(db_path)
if not os.path.exists(db_dir): os.makedirs(db_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'


# --- Extensions Initialization ---
db.init_app(app)
migrate = Migrate(app, db) # Keep Migrate init
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = "الرجاء تسجيل الدخول للوصول إلى هذه الصفحة."

# --- Context Processor ---
@app.context_processor
def utility_processor():
    def get_now(): return datetime.utcnow()
    return dict(now=get_now)

# --- User Loader ---
@login_manager.user_loader
def load_user(user_id):
    try: return User.query.get(int(user_id))
    except: return None

# --- Database Initialization Command ---
@app.cli.command('create-db')
def create_db_command(): _create_db_and_seed()

def _create_db_and_seed():
    # ... (seeding logic remains the same) ...
    with app.app_context():
        database = db or current_app.extensions['sqlalchemy'].db
        database.create_all()
        print("Database tables created.")
        if not User.query.first():
            print("Seeding initial users and Maslaks...")
            admin_user = User( username='admin', password=generate_password_hash('adminpassword', method='pbkdf2:sha256'), is_admin=True)
            database.session.add(admin_user)
            new_users = ['ahmed_a', 'ahmed_s', 'hakim', 'jawhar', 'mohamed', 'yassine']
            user_objects = {}
            for username in new_users:
                password = f"{username}2023"; hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                new_user = User(username=username, password=hashed_password, is_admin=False);
                user_objects[username] = new_user
                database.session.add(new_user)
                print(f"  Added user: {username} (password: {password})")
            maslak1 = Maslak(name="المسلك الأول: الأساسيات")
            maslak2 = Maslak(name="المسلك الثاني: المتقدم")
            database.session.add_all([maslak1, maslak2])
            print("  Added Maslaks.")
            database.session.commit()
            print(f"Initial users (admin + {len(new_users)}) and Maslaks seeded.")
        else: print("Database already contains data.")


# --- Helper Function for Logging Activity ---
def log_activity(action, user=None, target=None, details=None):
    """Logs an action to the AuditLog table."""
    try:
        log_user = user or (current_user if current_user.is_authenticated else None)
        user_id = log_user.id if log_user else None
        target_type = target.__class__.__name__ if target else None
        target_id = target.id if target and hasattr(target, 'id') else None
        details_str = json.dumps(details, ensure_ascii=False, default=str) if isinstance(details, dict) else details # Use default=str for complex objects

        log_entry = AuditLog( user_id=user_id, action=action, target_type=target_type, target_id=target_id, details=details_str )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error logging activity '{action}': {e}", exc_info=True)
# --- End Helper Function ---


# --- Custom Admin Forms ---
class UserForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('كلمة المرور (جديدة)', validators=[Optional(), EqualTo('confirm_password', message='يجب أن تتطابق كلمتا المرور')])
    confirm_password = PasswordField('تأكيد كلمة المرور')
    is_admin = BooleanField('مسؤول؟')

class MaslakForm(FlaskForm):
    name = StringField('اسم المسلك', validators=[DataRequired(), Length(max=100)])

# --- Flask-Admin Setup ---
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self): return current_user.is_authenticated and hasattr(current_user, 'is_admin') and current_user.is_admin
    def inaccessible_callback(self, name, **kwargs): flash('الرجاء تسجيل الدخول كمسؤول للوصول لهذه الصفحة.', 'warning'); return redirect(url_for('login', next=request.url))

class SecureModelView(ModelView):
    def is_accessible(self): return current_user.is_authenticated and hasattr(current_user, 'is_admin') and current_user.is_admin
    def inaccessible_callback(self, name, **kwargs): flash('الرجاء تسجيل الدخول كمسؤول للوصول لهذه الصفحة.', 'warning'); return redirect(url_for('login', next=request.url))

class UserAdminView(SecureModelView):
    form = UserForm
    column_list = ('id', 'username', 'is_admin', 'last_login', 'assigned_episodes')
    column_exclude_list = ('password', 'audit_logs')
    form_excluded_columns = ('comments', 'assigned_episodes', 'password', 'last_login', 'audit_logs')
    column_searchable_list = ('username',)
    column_display_pk = True
    column_sortable_list = ('id', 'username', 'is_admin', 'last_login')
    def on_model_change(self, form, model, is_created):
        if form.password.data: model.password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        elif is_created and not model.password: flash('كلمة المرور مطلوبة للمستخدمين الجدد.', 'error'); raise ValueError("Password required")
    def after_model_change(self, form, model, is_created):
        action = 'create_user' if is_created else 'edit_user'; log_activity(action, target=model, details=f"Admin action by {current_user.username}")
    def on_model_delete(self, model): log_activity('delete_user', target=model, details=f"Admin action by {current_user.username}")

class EpisodeAdminView(SecureModelView):
    column_list = ('id', 'title', 'maslak', 'status', 'display_order', 'last_updated', 'assignees')
    column_searchable_list = ('title', 'plan', 'scenario', 'maslak.name', 'status')
    column_filters = ('maslak', 'status')
    form_columns = ('title', 'maslak', 'status', 'plan', 'scenario', 'display_order')
    form_excluded_columns = ('comments', 'assignees', 'audit_logs')
    column_display_pk = True
    column_sortable_list = ('id', 'title', 'maslak.name', 'status', 'last_updated', 'display_order')
    form_overrides = { 'status': SelectField }
    form_args = { 'status': { 'label': 'الحالة', 'choices': EPISODE_STATUS_CHOICES } }
    def after_model_change(self, form, model, is_created):
        action = 'create_episode_admin' if is_created else 'edit_episode_admin'; log_activity(action, target=model, details=f"Admin action by {current_user.username}")
    def on_model_delete(self, model): log_activity('delete_episode_admin', target=model, details=f"Admin action by {current_user.username}")

class MaslakAdminView(SecureModelView):
    form = MaslakForm
    column_list = ('id', 'name', 'episodes')
    column_searchable_list = ('name',)
    column_display_pk = True
    form_excluded_columns = ('episodes',)
    def after_model_change(self, form, model, is_created):
        action = 'create_maslak' if is_created else 'edit_maslak'; log_activity(action, target=model, details=f"Admin action by {current_user.username}")
    def on_model_delete(self, model): log_activity('delete_maslak', target=model, details=f"Admin action by {current_user.username}")

class AuditLogAdminView(SecureModelView):
    # Use custom template to add Clear button
    list_template = 'admin/auditlog_list.html'

    can_create = False; can_edit = False; can_delete = False # Read-only view
    column_list = ('timestamp', 'user', 'action', 'target_type', 'target_id', 'details')
    column_searchable_list = ('action', 'target_type', 'details', 'user.username')
    column_filters = ('action', 'user', 'target_type', 'timestamp')
    column_default_sort = ('timestamp', True)
    column_labels = { 'user': 'المستخدم', 'timestamp': 'الوقت', 'action': 'الإجراء', 'target_type': 'نوع الهدف', 'target_id': 'معرف الهدف', 'details': 'تفاصيل' }

admin = Admin(app, name='صالح - الكراسة الحمراء 📕', template_mode='bootstrap4', url='/admin', index_view=MyAdminIndexView())
admin.add_view(UserAdminView(User, db.session, name='المستخدمون'))
admin.add_view(EpisodeAdminView(Episode, db.session, name='الحلقات'))
admin.add_view(MaslakAdminView(Maslak, db.session, name='المسالك'))
admin.add_view(AuditLogAdminView(AuditLog, db.session, name='سجل النشاط')) # Added Audit Log view
# --- End Flask-Admin Setup ---

# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            remember_me = bool(request.form.get('remember'))
            login_user(user, remember=remember_me)
            try:
                user.last_login = datetime.utcnow()
                # Log activity *after* potential commit for last_login
                # db.session.add(user) # No need to re-add
                db.session.commit() # Commit last_login first
                log_activity('login', user=user) # Now log
            except Exception as e:
                 db.session.rollback()
                 app.logger.error(f"Error updating last_login/logging for user {user.id}: {e}", exc_info=True)
            flash('تم تسجيل الدخول بنجاح.', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith(url_for('admin.index')):
                 if hasattr(user, 'is_admin') and user.is_admin: return redirect(next_page)
                 else: flash('ليس لديك صلاحية الوصول للوحة التحكم.', 'warning'); return redirect(url_for('dashboard'))
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صالحة.', 'danger')
            log_activity('login_failed', details=f"Username: {username}")
    return render_template('login.html')

# ... (Other routes remain largely the same, but with log_activity calls added) ...

@app.route('/logout')
@login_required
def logout():
    log_activity('logout')
    logout_user()
    flash('تم تسجيل خروجك.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    # ... (dashboard logic remains the same) ...
    app.logger.info(f"Accessing dashboard route for user: {current_user.username}")
    try:
        selected_maslak_id_str = request.args.get('maslak', default='', type=str)
        selected_status = request.args.get('status', default='')
        selected_maslak_id = None
        if selected_maslak_id_str:
            try:
                selected_maslak_id = int(selected_maslak_id_str)
                if not Maslak.query.get(selected_maslak_id): selected_maslak_id = None
            except ValueError: selected_maslak_id = None
        valid_statuses = [choice[0] for choice in EPISODE_STATUS_CHOICES]
        if selected_status and selected_status not in valid_statuses: selected_status = ''
        episode_query = Episode.query.options(joinedload(Episode.assignees))
        if selected_maslak_id: episode_query = episode_query.filter(Episode.maslak_id == selected_maslak_id)
        if selected_status: episode_query = episode_query.filter(Episode.status == selected_status)
        filtered_episodes = episode_query.order_by(Episode.display_order, Episode.id).all()
        total_episodes_in_view = len(filtered_episodes)
        draft_episodes = sum(1 for ep in filtered_episodes if ep.status == EPISODE_STATUS_DRAFT)
        review_episodes = sum(1 for ep in filtered_episodes if ep.status == EPISODE_STATUS_REVIEW)
        complete_episodes = sum(1 for ep in filtered_episodes if ep.status == EPISODE_STATUS_COMPLETE)
        metrics = { 'total_episodes': total_episodes_in_view, 'draft_episodes': draft_episodes, 'review_episodes': review_episodes, 'complete_episodes': complete_episodes, }
        all_maslaks = Maslak.query.order_by(Maslak.name).all()
        collaborators = User.query.filter(User.id != current_user.id).order_by(User.username).all()
        status_filter_options = EPISODE_STATUS_CHOICES
        return render_template('dashboard.html', all_episodes=filtered_episodes, all_maslaks=all_maslaks, selected_maslak_id=selected_maslak_id, selected_status=selected_status, status_filter_options=status_filter_options, collaborators=collaborators, metrics=metrics)
    except Exception as e: app.logger.error(f"Error in dashboard route: {e}", exc_info=True); abort(500)


@app.route('/test')
@login_required
def test_route(): return "Test route is working!"


@app.route('/create_episode', methods=['POST'])
@login_required
def create_episode():
    title = request.form.get('title'); maslak_id = request.form.get('maslak_id', type=int)
    if not title: flash('عنوان الحلقة لا يمكن أن يكون فارغًا.', 'danger'); return redirect(url_for('dashboard'))
    if not maslak_id: flash('يجب اختيار مسلك للحلقة.', 'danger'); return redirect(url_for('dashboard'))
    maslak = Maslak.query.get(maslak_id)
    if not maslak: flash('المسلك المحدد غير صالح.', 'danger'); return redirect(url_for('dashboard'))
    existing_episode = Episode.query.filter_by(title=title, maslak_id=maslak_id).first()
    if existing_episode: flash(f'حلقة بعنوان "{title}" موجودة بالفعل في هذا المسلك.', 'warning'); return redirect(url_for('dashboard', maslak=maslak_id))
    try:
        last_episode_in_maslak = Episode.query.filter_by(maslak_id=maslak_id).order_by(Episode.display_order.desc()).first()
        initial_order = (last_episode_in_maslak.display_order + 1) if last_episode_in_maslak else 0
        new_episode = Episode(title=title, maslak_id=maslak_id, display_order=initial_order)
        db.session.add(new_episode); db.session.flush()
        assignment = Assignment(user_id=current_user.id, episode_id=new_episode.id); db.session.add(assignment)
        log_activity('create_episode', target=new_episode)
        db.session.commit(); flash(f'تم إنشاء الحلقة "{title}" بنجاح في مسلك "{maslak.name}" وتم تعيينك لها.', 'success')
    except Exception as e: db.session.rollback(); flash(f'خطأ في إنشاء الحلقة: {e}', 'danger'); print(f"Error: {e}")
    return redirect(url_for('dashboard', maslak=maslak_id))


@app.route('/delete_episode/<int:episode_id>', methods=['POST'])
@login_required
def delete_episode(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
    if not is_assigned and not (hasattr(current_user, 'is_admin') and current_user.is_admin):
         flash('يمكن فقط للمستخدمين المعينين أو المسؤولين حذف الحلقات.', 'warning')
         return redirect(url_for('dashboard'))
    try:
        log_activity('delete_episode', target=episode)
        Assignment.query.filter_by(episode_id=episode.id).delete(); db.session.delete(episode); db.session.commit()
        flash(f'تم حذف الحلقة "{episode.title}" بنجاح.', 'success')
    except Exception as e: db.session.rollback(); flash(f'خطأ في حذف الحلقة: {e}', 'danger'); print(f"Error: {e}")
    return redirect(url_for('dashboard'))

@app.route('/episode/<int:episode_id>/change_maslak', methods=['POST'])
@login_required
def change_episode_maslak(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    new_maslak_id = request.form.get('new_maslak_id', type=int)
    is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
    user_is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    if not is_assigned and not user_is_admin: flash('فقط المستخدمون المعينون أو المسؤولون يمكنهم تغيير المسلك.', 'danger'); return redirect(url_for('view_episode', episode_id=episode_id))
    if not new_maslak_id: flash('لم يتم اختيار مسلك جديد.', 'warning'); return redirect(url_for('view_episode', episode_id=episode_id))
    new_maslak = Maslak.query.get(new_maslak_id)
    if not new_maslak: flash('المسلك الجديد المحدد غير صالح.', 'danger'); return redirect(url_for('view_episode', episode_id=episode_id))
    if episode.maslak_id == new_maslak_id: flash('الحلقة موجودة بالفعل في هذا المسلك.', 'info'); return redirect(url_for('view_episode', episode_id=episode_id))
    try:
        old_maslak_name = episode.maslak.name if episode.maslak else 'غير محدد'
        episode.maslak_id = new_maslak_id
        db.session.add(episode)
        log_activity('change_maslak', target=episode, details=f"New Maslak ID: {new_maslak_id}")
        db.session.commit()
        flash(f'تم نقل الحلقة "{episode.title}" من مسلك "{old_maslak_name}" إلى مسلك "{new_maslak.name}" بنجاح.', 'success')
    except Exception as e: db.session.rollback(); flash(f'حدث خطأ أثناء تغيير المسلك: {e}', 'danger'); app.logger.error(f"Error changing maslak for episode {episode_id}: {e}", exc_info=True)
    return redirect(url_for('view_episode', episode_id=episode_id))

@app.route('/episode/<int:episode_id>/change_status', methods=['POST'])
@login_required
def change_episode_status(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    new_status = request.form.get('new_status')
    is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
    user_is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    if not is_assigned and not user_is_admin: flash('فقط المستخدمون المعينون أو المسؤولون يمكنهم تغيير الحالة.', 'danger'); return redirect(url_for('view_episode', episode_id=episode_id))
    valid_statuses = [choice[0] for choice in EPISODE_STATUS_CHOICES]
    if not new_status or new_status not in valid_statuses: flash('الحالة المحددة غير صالحة.', 'warning'); return redirect(url_for('view_episode', episode_id=episode_id))
    if episode.status == new_status: flash('الحلقة لديها هذه الحالة بالفعل.', 'info'); return redirect(url_for('view_episode', episode_id=episode_id))
    try:
        episode.status = new_status
        db.session.add(episode)
        log_activity('change_status', target=episode, details=f"New Status: {new_status}")
        db.session.commit()
        flash(f'تم تغيير حالة الحلقة "{episode.title}" إلى "{new_status}" بنجاح.', 'success')
    except Exception as e: db.session.rollback(); flash(f'حدث خطأ أثناء تغيير الحالة: {e}', 'danger'); app.logger.error(f"Error changing status for episode {episode_id}: {e}", exc_info=True)
    return redirect(url_for('view_episode', episode_id=episode_id))


# --- NEW: Route to Clear Audit Log ---
@app.route('/admin/clear_audit_log', methods=['POST'])
@login_required
def clear_audit_log():
    """Clears all entries from the AuditLog table. Admin only."""
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin):
        flash('غير مصرح لك بهذا الإجراء.', 'danger')
        return redirect(url_for('admin.index')) # Redirect back to admin index

    try:
        num_rows_deleted = db.session.query(AuditLog).delete()
        log_activity('clear_audit_log', details=f"{num_rows_deleted} rows deleted.") # Log the clear action itself
        db.session.commit()
        flash(f'تم حذف جميع سجلات النشاط ({num_rows_deleted} سجل).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف السجلات: {e}', 'danger')
        app.logger.error(f"Error clearing audit log: {e}", exc_info=True)

    # Redirect back to the audit log view
    return redirect(url_for('auditlog.index_view'))
# --- End Clear Audit Log Route ---


@app.route('/api/update_episode_order', methods=['POST'])
@login_required
def update_episode_order():
    # ... (update_episode_order logic remains the same, but now logs) ...
    data = request.get_json();
    if not data or 'ordered_ids' not in data: return jsonify({'success': False, 'message': 'بيانات غير صالحة'}), 400
    ordered_ids = data['ordered_ids']; app.logger.info(f"Received new episode order: {ordered_ids}")
    try:
        for index, episode_id_str in enumerate(ordered_ids):
            try:
                episode_id = int(episode_id_str); episode = Episode.query.get(episode_id)
                if episode: episode.display_order = index; db.session.add(episode)
                else: app.logger.warning(f"Episode ID {episode_id} not found during reorder.")
            except ValueError: app.logger.warning(f"Invalid episode ID received: {episode_id_str}"); continue
        log_activity('reorder_episodes', details=f"New order: {ordered_ids}")
        db.session.commit(); app.logger.info("Episode order updated successfully.")
        return jsonify({'success': True, 'message': 'تم تحديث ترتيب الحلقات.'})
    except Exception as e: db.session.rollback(); app.logger.error(f"Error updating episode order: {e}", exc_info=True); return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث الترتيب.'}), 500


@app.route('/assign_user', methods=['POST'])
@login_required
def assign_user_to_episode():
    # ... (validation) ...
    episode_id = request.form.get('episode_id'); user_to_assign_id = request.form.get('user_to_assign_id')
    if not episode_id or not user_to_assign_id: flash('معرّف الحلقة أو المستخدم مفقود.', 'danger'); return redirect(request.referrer or url_for('dashboard'))
    try: episode_id = int(episode_id); user_to_assign_id = int(user_to_assign_id)
    except ValueError: flash('صيغة معرّف الحلقة أو المستخدم غير صالحة.', 'danger'); return redirect(request.referrer or url_for('dashboard'))
    episode = Episode.query.get(episode_id); user_to_assign = User.query.get(user_to_assign_id)
    if not episode or not user_to_assign: flash('الحلقة أو المستخدم غير موجود.', 'danger'); return redirect(url_for('dashboard'))
    existing_assignment = Assignment.query.filter_by(user_id=user_to_assign.id, episode_id=episode.id).first()
    if existing_assignment: flash(f'المستخدم "{user_to_assign.username}" معين بالفعل للحلقة "{episode.title}".', 'info'); return redirect(url_for('view_episode', episode_id=episode_id))
    try:
        new_assignment = Assignment(user_id=user_to_assign.id, episode_id=episode.id); db.session.add(new_assignment)
        log_activity('assign_user', target=episode, details=f"Assigned User ID: {user_to_assign_id}")
        db.session.commit()
        flash(f'تم تعيين المستخدم "{user_to_assign.username}" بنجاح للحلقة "{episode.title}".', 'success')
    except Exception as e: db.session.rollback(); flash(f'خطأ في تعيين المستخدم: {e}', 'danger'); print(f"Error: {e}")
    return redirect(url_for('view_episode', episode_id=episode_id))

@app.route('/unassign_self/<int:episode_id>', methods=['POST'])
@login_required
def unassign_self_from_episode(episode_id):
    # ... (validation) ...
    episode = Episode.query.get_or_404(episode_id)
    assignment = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).first()
    if assignment:
        try:
            log_activity('unassign_self', target=episode)
            db.session.delete(assignment); db.session.commit();
            flash(f'لقد قمت بإلغاء تعيين نفسك بنجاح من الحلقة "{episode.title}".', 'success')
        except Exception as e: db.session.rollback(); flash(f'خطأ في إلغاء تعيين نفسك: {e}', 'danger'); print(f"Error: {e}"); return redirect(url_for('view_episode', episode_id=episode_id))
    else: flash('لم تكن معينًا لهذه الحلقة.', 'info'); return redirect(url_for('view_episode', episode_id=episode_id))
    return redirect(url_for('dashboard'))

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    # ... (permission check) ...
    if comment.user_id != current_user.id and not (hasattr(current_user, 'is_admin') and current_user.is_admin):
        return jsonify({'success': False, 'message': 'غير مصرح لك بحذف هذا التعليق.'}), 403
    try:
        episode_id = comment.episode_id
        deleted_block_index = comment.block_index
        log_activity('delete_comment', target_id=episode_id, target_type='Episode', details=f"Comment ID: {comment_id}")
        db.session.delete(comment); db.session.commit()
        return jsonify({'success': True, 'message': 'تم حذف التعليق بنجاح.', 'deleted_comment_id': comment_id, 'deleted_block_index': deleted_block_index})
    except Exception as e: db.session.rollback(); print(f"Error: {e}"); return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف التعليق.'}), 500

@app.route('/episode/<int:episode_id>', methods=['GET'])
@login_required
def view_episode(episode_id):
    # ... (view_episode logic remains the same) ...
    episode = Episode.query.options(joinedload(Episode.assignees), joinedload(Episode.maslak)).get_or_404(episode_id)
    current_user_is_assigned = any(assignee.id == current_user.id for assignee in episode.assignees)
    all_users = User.query.order_by(User.username).all()
    all_maslaks = Maslak.query.order_by(Maslak.name).all()
    comments_query = episode.comments.options(subqueryload(Comment.author))
    comments = comments_query.order_by(Comment.block_index, Comment.timestamp).all()
    comments_by_block = {}
    for comment in comments:
        block_idx = comment.block_index
        if block_idx not in comments_by_block: comments_by_block[block_idx] = []
        author_username = comment.author.username if comment.author else "مستخدم غير معروف"
        author_id = comment.author.id if comment.author else None
        comments_by_block[block_idx].append({'id': comment.id, 'text': comment.text, 'author': author_username, 'author_id': author_id, 'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M')})
    user_is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    return render_template('episode.html', episode=episode, comments_by_block=comments_by_block, is_assigned=current_user_is_assigned, all_users=all_users, all_maslaks=all_maslaks, user_is_admin=user_is_admin, status_choices=EPISODE_STATUS_CHOICES)


@app.route('/episode/<int:episode_id>/update', methods=['POST'])
@login_required
def update_episode(episode_id):
     episode = Episode.query.get_or_404(episode_id); is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
     if not is_assigned: return jsonify({'success': False, 'message': 'غير مصرح لك. يجب أن تكون معينًا للتعديل.'}), 403
     data = request.json; updated = False; details_log = []
     if 'plan' in data and data['plan'] != episode.plan:
         episode.plan = data['plan']; updated = True; details_log.append('plan')
     if 'scenario' in data and data['scenario'] != episode.scenario:
         episode.scenario = data['scenario']; updated = True; details_log.append('scenario')
     if updated:
         try:
             db.session.add(episode)
             log_activity('update_content', target=episode, details=f"Updated: {', '.join(details_log)}")
             db.session.commit();
             return jsonify({'success': True, 'message': 'تم تحديث الحلقة بنجاح'})
         except Exception as e: db.session.rollback(); print(f"Error: {e}"); return jsonify({'success': False, 'message': 'خطأ في تحديث الحلقة'}), 500
     else: return jsonify({'success': True, 'message': 'لم يتم اكتشاف أي تغييرات'})


@app.route('/api/episode/<int:episode_id>/update_title', methods=['POST'])
@login_required
def update_episode_title(episode_id):
    # ... (validation, permission check) ...
    episode = Episode.query.get_or_404(episode_id)
    data = request.get_json()
    if not data or 'new_title' not in data: return jsonify({'success': False, 'message': 'بيانات غير صالحة'}), 400
    new_title = data['new_title'].strip()
    if not new_title: return jsonify({'success': False, 'message': 'العنوان لا يمكن أن يكون فارغًا'}), 400
    is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
    user_is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    if not is_assigned and not user_is_admin: return jsonify({'success': False, 'message': 'غير مصرح لك بتعديل هذا العنوان'}), 403
    existing = Episode.query.filter(Episode.maslak_id == episode.maslak_id, Episode.title == new_title, Episode.id != episode_id).first()
    if existing: return jsonify({'success': False, 'message': f'عنوان الحلقة "{new_title}" مستخدم بالفعل في هذا المسلك.'}), 400
    try:
        old_title = episode.title
        episode.title = new_title
        log_activity('update_title', target=episode, details=f"Old: '{old_title}', New: '{new_title}'")
        db.session.commit()
        app.logger.info(f"Updated title for episode {episode_id} to '{new_title}' by user {current_user.username}")
        return jsonify({'success': True, 'message': 'تم تحديث العنوان بنجاح', 'new_title': new_title})
    except Exception as e: db.session.rollback(); app.logger.error(f"Error updating title for episode {episode_id}: {e}", exc_info=True); return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث العنوان'}), 500

@app.route('/episode/<int:episode_id>/comments', methods=['POST'])
@login_required
def add_comment(episode_id):
    # ... (validation, permission check) ...
    episode = Episode.query.get_or_404(episode_id); is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
    if not is_assigned: return jsonify({'success': False, 'message': 'غير مصرح لك. يجب أن تكون معينًا للتعليق.'}), 403
    data = request.json; block_index = data.get('block_index'); text = data.get('text')
    if block_index is None or not isinstance(text, str) or not text.strip(): return jsonify({'success': False, 'message': 'معرّف الفقرة أو نص التعليق مفقود أو غير صالح'}), 400
    try:
        block_index = int(block_index);
        if block_index < 0: return jsonify({'success': False, 'message': 'معرّف الفقرة غير صالح'}), 400
        comment = Comment(episode_id=episode.id, user_id=current_user.id, block_index=block_index, text=text.strip())
        db.session.add(comment)
        log_activity('add_comment', target=episode, details=f"Block: {block_index}")
        db.session.commit()
        return jsonify({'success': True, 'message': 'تمت إضافة التعليق', 'comment': {'id': comment.id, 'block_index': comment.block_index, 'text': comment.text, 'author': current_user.username, 'author_id': current_user.id, 'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M')}}), 201
    except ValueError: return jsonify({'success': False, 'message': 'صيغة معرّف الفقرة غير صالحة'}), 400
    except Exception as e: db.session.rollback(); print(f"Error: {e}"); return jsonify({'success': False, 'message': 'خطأ في إضافة التعليق'}), 500

# --- PDF Export Route ---
@app.route('/episode/<int:episode_id>/export/pdf')
@login_required
def export_episode_pdf(episode_id):
    # ... (export_episode_pdf logic remains the same) ...
    episode = Episode.query.get_or_404(episode_id)
    plan_html = markdown.markdown(episode.plan or '', extensions=['extra', 'tables', 'fenced_code'])
    scenario_html = markdown.markdown(episode.scenario or '', extensions=['extra', 'tables', 'fenced_code'])
    html_string = f""" <!DOCTYPE html> <html lang="ar" dir="rtl"> <head> <meta charset="UTF-8"> <title>Export: {episode.title}</title> <link rel="preconnect" href="https://fonts.googleapis.com"> <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin> <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&family=IBM+Plex+Sans+Arabic:wght@400;500;700&display=swap" rel="stylesheet"> <style> @page {{ margin: 1.5cm; }} body {{ font-family: 'Tajawal', sans-serif; direction: rtl; text-align: right; line-height: 1.5; }} h1, h2 {{ font-family: 'Tajawal', sans-serif; font-weight: bold; margin-top: 1.5em; margin-bottom: 0.5em; color: #1f2937; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }} h1 {{ font-size: 20pt; }} h2 {{ font-size: 16pt; }} p, li, td, th {{ font-family: 'IBM Plex Sans Arabic', sans-serif; font-size: 11pt; margin-bottom: 0.6em; }} ul, ol {{ padding-right: 25px; margin-bottom: 1em; }} li {{ margin-bottom: 0.3em; }} strong {{ font-weight: bold; }} em {{ font-style: italic; }} hr {{ margin: 2em 0; border-top: 1px solid #ccc; }} table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; font-size: 10pt; }} th, td {{ border: 1px solid #ccc; padding: 8px; text-align: right; }} th {{ background-color: #f2f2f2; font-weight: bold; font-family: 'Tajawal', sans-serif; }} pre {{ background-color: #f8f8f8; border: 1px solid #ddd; padding: 10px; font-family: monospace; white-space: pre-wrap; word-wrap: break-word; direction: ltr; text-align: left; margin-bottom: 1em; }} code {{ font-family: monospace; }} blockquote {{ border-right: 3px solid #ccc; padding-right: 10px; margin-right: 0; margin-left: 0; color: #666; font-style: italic; }} </style> </head> <body> <h1>{episode.title or 'بيانات الحلقة'}</h1> <h2>خطة الحلقة</h2> <div>{plan_html or '<p><i>(لا توجد خطة)</i></p>'}</div> <hr> <h2>السيناريو</h2> <div>{scenario_html or '<p><i>(لا يوجد سيناريو)</i></p>'}</div> </body> </html> """
    try:
        html = HTML(string=html_string); pdf_bytes = html.write_pdf()
        pdf_io = io.BytesIO(pdf_bytes); safe_title = (episode.title or 'episode').replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"episode_{episode.id}_{safe_title}.pdf"
        return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name=filename)
    except Exception as e: app.logger.error(f"Error generating PDF for episode {episode_id}: {e}", exc_info=True); flash("حدث خطأ أثناء إنشاء ملف PDF.", "danger"); return redirect(url_for('view_episode', episode_id=episode_id))


# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(db_path):
            print("Database file not found. Creating tables and seeding data...")
            _create_db_and_seed()
    app.run(debug=True)

