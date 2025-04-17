# models.py
# Defines the database structure for the application using SQLAlchemy.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy extension
db = SQLAlchemy()

# --- Default Markdown Template for Plan ---
DEFAULT_PLAN_MARKDOWN = """## ✅ مؤشرات نجاح الحلقة
(أدخل مؤشرات النجاح هنا)

---

## 📝 التكليف
(أدخل تفاصيل التكليف هنا)

---

## 🧑‍💻 تصور عملي تقريبي للحلقة (تجربة المستخدم)
(صف تجربة المستخدم هنا)

---

## 📖 المراجع من القرآن والسنّة
(أدخل الآيات أو الأحاديث المرتبطة بالحلقة)

---

## 🎯 الهدف من الحلقة (SMART Goal)
(حدّد الهدف بشكل واضح وقابل للقياس)

---

## 💬 مواضيع الحلقة
(أدرج المواضيع التي ستتم مناقشتها)

---"""
# --- End Default Template ---


# User model: Represents users who can log in and contribute.
# Inherits from UserMixin for Flask-Login compatibility.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False) # Stores the hashed password
    is_admin = db.Column(db.Boolean, nullable=False, default=False) # Admin flag

    # Relationship to episodes assigned to this user
    assigned_episodes = db.relationship('Episode', secondary='assignment', back_populates='assignees')
    # Relationship defining comments made by the user (backref defined in Comment)
    # Cascade delete for comments is now handled by the backref below

    def __repr__(self):
        return f'<User {self.username}>'

# Episode model: Represents an individual episode scenario.
class Episode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    # Set the default value for the plan column
    plan = db.Column(db.Text, nullable=True, default=DEFAULT_PLAN_MARKDOWN) # <<< UPDATED DEFAULT
    scenario = db.Column(db.Text, nullable=True, default='') # Section for the scenario script
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationship to users assigned to this episode
    assignees = db.relationship('User', secondary='assignment', back_populates='assigned_episodes')
    # Relationship to comments made on this episode
    # Keep lazy='dynamic' if filtering/complex queries on comments are needed later
    comments = db.relationship('Comment', backref='episode', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Episode {self.title}>'

# Assignment model: Many-to-many relationship between Users and Episodes.
# This table links users to the episodes they are assigned to work on.
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)

    # Define composite unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('user_id', 'episode_id', name='_user_episode_uc'),)


# Comment model: Represents comments made on specific blocks of an episode's scenario.
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Changed from line_number to block_index
    block_index = db.Column(db.Integer, nullable=False) # Index of the block (paragraph, heading, etc.)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationship to the user who made the comment
    # Added cascade='all, delete-orphan' to the backref for 'comments' on the User model
    author = db.relationship('User', backref=db.backref('comments', cascade='all, delete-orphan', lazy='dynamic'))

    def __repr__(self):
        return f'<Comment by User {self.user_id} on Episode {self.episode_id} Block {self.block_index}>'

