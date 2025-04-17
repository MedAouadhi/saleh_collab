# app.py
# Main Flask application file for the collaborative scenario writer (Arabic Version).

import os
import io # For handling PDF in memory
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, session, abort, current_app, send_file) # Added send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# Import models and db instance
# Make sure Assignment is imported to handle deletion cascade/manual removal
from models import db, User, Episode, Assignment, Comment # Ensure Comment model is imported
from dotenv import load_dotenv
from sqlalchemy.orm import joinedload, subqueryload
from werkzeug.security import generate_password_hash, check_password_hash
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

# --- PDF Generation Imports ---
import markdown
from weasyprint import HTML, CSS
# --- End PDF Imports ---


# Load environment variables from .env file (optional, good practice)
load_dotenv()

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key_arabic')
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
db_dir = os.path.dirname(db_path)
if not os.path.exists(db_dir): os.makedirs(db_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'


# --- Extensions Initialization ---
db.init_app(app)
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

# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    try:
        user_id_int = int(user_id)
        return User.query.get(user_id_int)
    except (ValueError, TypeError):
        return None

# --- Database Initialization Command ---
@app.cli.command('create-db')
def create_db_command(): _create_db_and_seed()

def _create_db_and_seed():
    """Helper function for database creation and seeding."""
    with app.app_context():
        # Ensure using the correct db instance tied to the app context
        database = db or current_app.extensions['sqlalchemy'].db
        database.create_all()
        print("Database tables created.")

        # Seed initial data (optional, for demonstration)
        if not User.query.first():
            print("Seeding initial users...")
            # Keep admin user
            admin_user = User(
                username='admin',
                password=generate_password_hash('adminpassword', method='pbkdf2:sha256'),
                is_admin=True
            )
            database.session.add(admin_user)

            # Add new specified users
            new_users = ['ahmed_a', 'ahmed_s', 'hakim', 'jawhar', 'mohamed', 'yassine']
            for username in new_users:
                password = f"{username}2023"
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                new_user = User(username=username, password=hashed_password, is_admin=False)
                database.session.add(new_user)
                print(f"  Added user: {username} (password: {password})") # Log for confirmation

            # --- REMOVED Default Episode Creation ---
            # ep1 = Episode(...)
            # ep2 = Episode(...)
            # ep3 = Episode(...)
            # database.session.add_all([ep1, ep2, ep3])
            # database.session.commit() # Commit users and episodes first to get IDs

            # --- REMOVED Default Assignment Creation ---
            # assign1 = Assignment(...)
            # ...
            # database.session.add_all([...])

            # --- REMOVED Default Comment Creation ---
            # comment1 = Comment(...)
            # database.session.add(comment1)

            database.session.commit() # Commit users
            print("Initial users seeded. No default episodes/assignments/comments were added.")
        else: print("Database already contains data.")

# --- Custom Admin Forms ---
class UserForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('كلمة المرور (جديدة)', validators=[Optional(), EqualTo('confirm_password', message='يجب أن تتطابق كلمتا المرور')])
    confirm_password = PasswordField('تأكيد كلمة المرور')
    is_admin = BooleanField('مسؤول؟')

# --- Flask-Admin Setup ---
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self): return current_user.is_authenticated and hasattr(current_user, 'is_admin') and current_user.is_admin
    def inaccessible_callback(self, name, **kwargs): flash('الرجاء تسجيل الدخول كمسؤول للوصول لهذه الصفحة.', 'warning'); return redirect(url_for('login', next=request.url))

class SecureModelView(ModelView):
    def is_accessible(self): return current_user.is_authenticated and hasattr(current_user, 'is_admin') and current_user.is_admin
    def inaccessible_callback(self, name, **kwargs): flash('الرجاء تسجيل الدخول كمسؤول للوصول لهذه الصفحة.', 'warning'); return redirect(url_for('login', next=request.url))

class UserAdminView(SecureModelView):
    form = UserForm
    column_list = ('id', 'username', 'is_admin', 'assigned_episodes')
    column_exclude_list = ('password',)
    form_excluded_columns = ('comments', 'assigned_episodes', 'password')
    column_searchable_list = ('username',)
    column_display_pk = True
    def on_model_change(self, form, model, is_created):
        if form.password.data: model.password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        elif is_created and not model.password: flash('كلمة المرور مطلوبة للمستخدمين الجدد.', 'error'); raise ValueError("Password required")

class EpisodeAdminView(SecureModelView):
    column_list = ('id', 'title', 'last_updated', 'assignees')
    column_searchable_list = ('title', 'plan', 'scenario')
    form_excluded_columns = ('comments', 'assignees')
    column_display_pk = True

admin = Admin(app, name='لوحة تحكم السناريو', template_mode='bootstrap4', url='/admin', index_view=MyAdminIndexView())
admin.add_view(UserAdminView(User, db.session, name='المستخدمون'))
admin.add_view(EpisodeAdminView(Episode, db.session, name='الحلقات'))
# --- End Flask-Admin Setup ---

# --- Routes ---
# ... (Routes remain the same) ...
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=request.form.get('remember'))
            flash('تم تسجيل الدخول بنجاح.', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith(url_for('admin.index')):
                 if hasattr(user, 'is_admin') and user.is_admin: return redirect(next_page)
                 else: flash('ليس لديك صلاحية الوصول للوحة التحكم.', 'warning'); return redirect(url_for('dashboard'))
            return redirect(next_page or url_for('dashboard'))
        else: flash('اسم المستخدم أو كلمة المرور غير صالحة.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); flash('تم تسجيل خروجك.', 'success'); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    app.logger.info(f"Accessing dashboard route for user: {current_user.username}")
    try:
        all_episodes = Episode.query.options(joinedload(Episode.assignees)).order_by(Episode.id).all()
        collaborators = User.query.filter(User.id != current_user.id).order_by(User.username).all()
        return render_template('dashboard.html', all_episodes=all_episodes, collaborators=collaborators)
    except Exception as e: app.logger.error(f"Error in dashboard route: {e}", exc_info=True); abort(500)

@app.route('/test')
@login_required
def test_route(): return "Test route is working!"

@app.route('/create_episode', methods=['POST'])
@login_required
def create_episode():
    title = request.form.get('title')
    if not title: flash('عنوان الحلقة لا يمكن أن يكون فارغًا.', 'danger'); return redirect(url_for('dashboard'))
    existing_episode = Episode.query.filter_by(title=title).first()
    if existing_episode: flash(f'حلقة بعنوان "{title}" موجودة بالفعل.', 'warning'); return redirect(url_for('dashboard'))
    try:
        new_episode = Episode(title=title)
        db.session.add(new_episode); db.session.flush()
        assignment = Assignment(user_id=current_user.id, episode_id=new_episode.id); db.session.add(assignment)
        db.session.commit(); flash(f'تم إنشاء الحلقة "{title}" بنجاح وتم تعيينك لها.', 'success')
    except Exception as e: db.session.rollback(); flash(f'خطأ في إنشاء الحلقة: {e}', 'danger'); print(f"Error: {e}")
    return redirect(url_for('dashboard'))

@app.route('/delete_episode/<int:episode_id>', methods=['POST'])
@login_required
def delete_episode(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
    if not is_assigned and not (hasattr(current_user, 'is_admin') and current_user.is_admin):
         flash('يمكن فقط للمستخدمين المعينين أو المسؤولين حذف الحلقات.', 'warning')
         return redirect(url_for('dashboard'))
    try:
        Assignment.query.filter_by(episode_id=episode.id).delete(); db.session.delete(episode); db.session.commit()
        flash(f'تم حذف الحلقة "{episode.title}" بنجاح.', 'success')
    except Exception as e: db.session.rollback(); flash(f'خطأ في حذف الحلقة: {e}', 'danger'); print(f"Error: {e}")
    return redirect(url_for('dashboard'))

@app.route('/assign_user', methods=['POST'])
@login_required
def assign_user_to_episode():
    episode_id = request.form.get('episode_id'); user_to_assign_id = request.form.get('user_to_assign_id')
    if not episode_id or not user_to_assign_id: flash('معرّف الحلقة أو المستخدم مفقود.', 'danger'); return redirect(request.referrer or url_for('dashboard'))
    try: episode_id = int(episode_id); user_to_assign_id = int(user_to_assign_id)
    except ValueError: flash('صيغة معرّف الحلقة أو المستخدم غير صالحة.', 'danger'); return redirect(request.referrer or url_for('dashboard'))
    episode = Episode.query.get(episode_id); user_to_assign = User.query.get(user_to_assign_id)
    if not episode or not user_to_assign: flash('الحلقة أو المستخدم غير موجود.', 'danger'); return redirect(url_for('dashboard'))
    existing_assignment = Assignment.query.filter_by(user_id=user_to_assign.id, episode_id=episode.id).first()
    if existing_assignment: flash(f'المستخدم "{user_to_assign.username}" معين بالفعل للحلقة "{episode.title}".', 'info'); return redirect(url_for('view_episode', episode_id=episode_id))
    try:
        new_assignment = Assignment(user_id=user_to_assign.id, episode_id=episode.id); db.session.add(new_assignment); db.session.commit()
        flash(f'تم تعيين المستخدم "{user_to_assign.username}" بنجاح للحلقة "{episode.title}".', 'success')
    except Exception as e: db.session.rollback(); flash(f'خطأ في تعيين المستخدم: {e}', 'danger'); print(f"Error: {e}")
    return redirect(url_for('view_episode', episode_id=episode_id))

@app.route('/unassign_self/<int:episode_id>', methods=['POST'])
@login_required
def unassign_self_from_episode(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    assignment = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).first()
    if assignment:
        try: db.session.delete(assignment); db.session.commit(); flash(f'لقد قمت بإلغاء تعيين نفسك بنجاح من الحلقة "{episode.title}".', 'success')
        except Exception as e: db.session.rollback(); flash(f'خطأ في إلغاء تعيين نفسك: {e}', 'danger'); print(f"Error: {e}"); return redirect(url_for('view_episode', episode_id=episode_id))
    else: flash('لم تكن معينًا لهذه الحلقة.', 'info'); return redirect(url_for('view_episode', episode_id=episode_id))
    return redirect(url_for('dashboard'))

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id and not (hasattr(current_user, 'is_admin') and current_user.is_admin):
        return jsonify({'success': False, 'message': 'غير مصرح لك بحذف هذا التعليق.'}), 403
    try:
        deleted_block_index = comment.block_index; db.session.delete(comment); db.session.commit()
        return jsonify({'success': True, 'message': 'تم حذف التعليق بنجاح.', 'deleted_comment_id': comment_id, 'deleted_block_index': deleted_block_index})
    except Exception as e: db.session.rollback(); print(f"Error: {e}"); return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف التعليق.'}), 500

@app.route('/episode/<int:episode_id>', methods=['GET'])
@login_required
def view_episode(episode_id):
    episode = Episode.query.options(joinedload(Episode.assignees)).get_or_404(episode_id)
    current_user_is_assigned = any(assignee.id == current_user.id for assignee in episode.assignees)
    all_users = User.query.order_by(User.username).all()
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
    return render_template('episode.html', episode=episode, comments_by_block=comments_by_block, is_assigned=current_user_is_assigned, all_users=all_users, user_is_admin=user_is_admin)

@app.route('/episode/<int:episode_id>/update', methods=['POST'])
@login_required
def update_episode(episode_id):
     episode = Episode.query.get_or_404(episode_id); is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
     if not is_assigned: return jsonify({'success': False, 'message': 'غير مصرح لك. يجب أن تكون معينًا للتعديل.'}), 403
     data = request.json; updated = False
     if 'plan' in data and data['plan'] != episode.plan: episode.plan = data['plan']; updated = True
     if 'scenario' in data and data['scenario'] != episode.scenario: episode.scenario = data['scenario']; updated = True
     if updated:
         try: db.session.add(episode); db.session.commit(); return jsonify({'success': True, 'message': 'تم تحديث الحلقة بنجاح'})
         except Exception as e: db.session.rollback(); print(f"Error: {e}"); return jsonify({'success': False, 'message': 'خطأ في تحديث الحلقة'}), 500
     else: return jsonify({'success': True, 'message': 'لم يتم اكتشاف أي تغييرات'})

@app.route('/episode/<int:episode_id>/comments', methods=['POST'])
@login_required
def add_comment(episode_id):
    episode = Episode.query.get_or_404(episode_id); is_assigned = Assignment.query.filter_by(user_id=current_user.id, episode_id=episode.id).count() > 0
    if not is_assigned: return jsonify({'success': False, 'message': 'غير مصرح لك. يجب أن تكون معينًا للتعليق.'}), 403
    data = request.json; block_index = data.get('block_index'); text = data.get('text')
    if block_index is None or not isinstance(text, str) or not text.strip(): return jsonify({'success': False, 'message': 'معرّف الفقرة أو نص التعليق مفقود أو غير صالح'}), 400
    try:
        block_index = int(block_index);
        if block_index < 0: return jsonify({'success': False, 'message': 'معرّف الفقرة غير صالح'}), 400
        comment = Comment(episode_id=episode.id, user_id=current_user.id, block_index=block_index, text=text.strip())
        db.session.add(comment); db.session.commit()
        return jsonify({'success': True, 'message': 'تمت إضافة التعليق', 'comment': {'id': comment.id, 'block_index': comment.block_index, 'text': comment.text, 'author': current_user.username, 'author_id': current_user.id, 'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M')}}), 201
    except ValueError: return jsonify({'success': False, 'message': 'صيغة معرّف الفقرة غير صالحة'}), 400
    except Exception as e: db.session.rollback(); print(f"Error: {e}"); return jsonify({'success': False, 'message': 'خطأ في إضافة التعليق'}), 500

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
    # Create the database tables if the db file doesn't exist
    # This is convenient for development but use `flask create-db` for explicit control
    with app.app_context():
        if not os.path.exists(db_path):
            print("Database file not found. Creating tables and seeding data...")
            _create_db_and_seed() # Call the helper function

    app.run(debug=True) # Enable debug mode for development (auto-reloads, detailed errors)

