# models.py
# Defines the database structure for the application using SQLAlchemy.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy extension
db = SQLAlchemy()

# --- Default Markdown Template for Plan ---
DEFAULT_PLAN_MARKDOWN = """
## 🎯 الأهداف من الحلقة 
(حدّد الهدف بشكل واضح وقابل للقياس)

---

## 💬 مواضيع الحلقة
(أدرج المواضيع التي ستتم مناقشتها)

---

## 📖 المراجع من القرآن والسنّة
(أدخل الآيات أو الأحاديث المرتبطة بالحلقة)

---

## 🧑‍💻 تصور عملي تقريبي للحلقة (تجربة المستخدم)
(صف تجربة المستخدم هنا)

---

## 📝 التكليف
(أدخل تفاصيل التكليف هنا)

---

## ✅ مؤشرات نجاح الحلقة
(أدخل مؤشرات النجاح هنا)

---"""
# --- End Default Template ---

# --- Episode Status Choices ---
EPISODE_STATUS_DRAFT = "لم يبدأ"
EPISODE_STATUS_REVIEW = "للمراجعة"
EPISODE_STATUS_COMPLETE = "مكتمل"
EPISODE_STATUS_CHOICES = [
    (EPISODE_STATUS_DRAFT, "لم يبدأ / Draft"),
    (EPISODE_STATUS_REVIEW, "للمراجعة / Review"),
    (EPISODE_STATUS_COMPLETE, "مكتمل / Complete"),
]
# --- End Status Choices ---


# Maslak (Chapter/Category) Model
class Maslak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<Maslak {self.name}>"


# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    # --- NEW: Last Login Timestamp ---
    last_login = db.Column(db.DateTime, nullable=True)
    # --- End Last Login ---

    assigned_episodes = db.relationship(
        "Episode", secondary="assignment", back_populates="assignees"
    )
    # comments backref defined below
    # audit_logs backref defined below

    def __repr__(self):
        return f"<User {self.username}>"


# Episode model
class Episode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    plan = db.Column(db.Text, nullable=True, default=DEFAULT_PLAN_MARKDOWN)
    scenario = db.Column(db.Text, nullable=True, default="")
    last_updated = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
    status = db.Column(
        db.String(50), nullable=False, default=EPISODE_STATUS_DRAFT, index=True
    )
    maslak_id = db.Column(db.Integer, db.ForeignKey("maslak.id"), nullable=False)
    maslak = db.relationship(
        "Maslak",
        backref=db.backref(
            "episodes", lazy="dynamic", order_by="Episode.display_order"
        ),
    )
    assignees = db.relationship(
        "User", secondary="assignment", back_populates="assigned_episodes"
    )
    comments = db.relationship(
        "Comment", backref="episode", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Episode {self.title}>"


# Assignment model
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    episode_id = db.Column(
        db.Integer, db.ForeignKey("episode.id", ondelete="CASCADE"), nullable=False
    )
    __table_args__ = (
        db.UniqueConstraint("user_id", "episode_id", name="_user_episode_uc"),
    )


# Comment model
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    episode_id = db.Column(
        db.Integer, db.ForeignKey("episode.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    block_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User", backref=db.backref("comments", lazy="dynamic"))

    def __repr__(self):
        return f"<Comment by User {self.user_id} on Episode {self.episode_id} Block {self.block_index}>"


# --- NEW: Audit Log Model ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    # Link to user, make nullable in case action is system-related or user is deleted later?
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    action = db.Column(
        db.String(100), nullable=False, index=True
    )  # e.g., 'login', 'create_episode', 'update_plan'
    target_type = db.Column(
        db.String(50), nullable=True, index=True
    )  # e.g., 'Episode', 'Comment', 'User'
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(
        db.Text, nullable=True
    )  # e.g., JSON string of changes, or simple description

    user = db.relationship("User", backref=db.backref("audit_logs", lazy="dynamic"))

    def __repr__(self):
        return f"<AuditLog {self.timestamp} User:{self.user_id} Action:{self.action}>"


# --- End Audit Log Model ---


# Scene model (مشهد)
class Scene(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    episode_id = db.Column(db.Integer, db.ForeignKey("episode.id", ondelete="CASCADE"), nullable=False)
    number = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    episode = db.relationship("Episode", backref=db.backref("scenes", lazy="dynamic", cascade="all, delete-orphan"))
    generations = db.relationship("VideoGeneration", backref="scene", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("episode_id", "number", name="_episode_scene_number_uc"),
    )

    def __repr__(self):
        return f"<Scene {self.number} of Episode {self.episode_id}>"


# VideoGeneration model (عملية توليد)
class VideoGeneration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scene_id = db.Column(db.Integer, db.ForeignKey("scene.id", ondelete="CASCADE"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(100), nullable=False)
    resolution = db.Column(db.String(20), nullable=True)
    aspect_ratio = db.Column(db.String(10), nullable=True)
    generate_audio = db.Column(db.Boolean, nullable=False, default=True)
    duration = db.Column(db.Integer, nullable=True)

    # OpenRouter job tracking
    job_id = db.Column(db.String(100), nullable=True, index=True)
    polling_url = db.Column(db.String(500), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )  # pending, in_progress, completed, failed, cancelled, expired

    unsigned_url = db.Column(db.Text, nullable=True)
    drive_file_id = db.Column(db.String(100), nullable=True)
    drive_view_url = db.Column(db.Text, nullable=True)
    local_path = db.Column(db.Text, nullable=True)
    cost = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    creator = db.relationship("User", backref=db.backref("video_generations", lazy="dynamic"))

    def __repr__(self):
        return f"<VideoGeneration {self.id} status={self.status}>"
