# routes_video.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Episode, Scene, VideoGeneration, Assignment
from video_service import VideoService
import os

video_bp = Blueprint("video", __name__, url_prefix="/api")


def _is_assigned_or_admin(episode_id):
    if hasattr(current_user, "is_admin") and current_user.is_admin:
        return True
    return (
        Assignment.query.filter_by(
            user_id=current_user.id, episode_id=episode_id
        ).count()
        > 0
    )


# --- Models ---
@video_bp.route("/models", methods=["GET"])
@login_required
def get_video_models():
    models = VideoService.get_cached_models()
    if not models:
        return jsonify({"success": False, "message": "OpenRouter غير متاح حالياً."}), 503
    return jsonify({"success": True, "models": models})


# --- Scenes ---
@video_bp.route("/episodes/<int:episode_id>/scenes", methods=["POST"])
@login_required
def create_scene(episode_id):
    if not _is_assigned_or_admin(episode_id):
        return jsonify({"success": False, "message": "غير مصرح لك."}), 403

    episode = Episode.query.get_or_404(episode_id)
    max_num = db.session.query(db.func.max(Scene.number)).filter_by(episode_id=episode_id).scalar() or 0
    new_scene = Scene(episode_id=episode_id, number=max_num + 1)
    db.session.add(new_scene)
    db.session.commit()
    return jsonify({"success": True, "scene": {"id": new_scene.id, "number": new_scene.number}}), 201


@video_bp.route("/scenes/<int:scene_id>", methods=["DELETE"])
@login_required
def delete_scene(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    if not _is_assigned_or_admin(scene.episode_id):
        return jsonify({"success": False, "message": "غير مصرح لك."}), 403

    # Delete local files and Drive files for all generations
    for gen in scene.generations:
        if gen.local_path and os.path.exists(gen.local_path):
            os.remove(gen.local_path)
        if gen.drive_file_id:
            VideoService.delete_from_drive(gen.drive_file_id)

    db.session.delete(scene)
    db.session.commit()
    return jsonify({"success": True, "message": "تم حذف المشهد."})


# --- Generations ---
@video_bp.route("/scenes/<int:scene_id>/generations", methods=["POST"])
@login_required
def create_generation(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    if not _is_assigned_or_admin(scene.episode_id):
        return jsonify({"success": False, "message": "غير مصرح لك."}), 403

    data = request.get_json()
    prompt = data.get("prompt", "").strip()
    model = data.get("model", "").strip()
    if not prompt or not model:
        return jsonify({"success": False, "message": "النص والموديل مطلوبان."}), 400

    try:
        result = VideoService.submit_generation(
            prompt=prompt,
            model=model,
            resolution=data.get("resolution"),
            aspect_ratio=data.get("aspect_ratio"),
            generate_audio=data.get("generate_audio", True),
            duration=data.get("duration"),
        )
        current_app.logger.info(f"[OpenRouter] submit_generation response: {result}")
    except Exception as e:
        current_app.logger.error(f"OpenRouter submit error: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"خطأ في إرسال الطلب: {e}"}), 500

    gen = VideoGeneration(
        scene_id=scene_id,
        prompt=prompt,
        model=model,
        resolution=data.get("resolution"),
        aspect_ratio=data.get("aspect_ratio"),
        generate_audio=data.get("generate_audio", True),
        duration=data.get("duration"),
        job_id=result.get("id"),
        polling_url=result.get("polling_url"),
        status=result.get("status", "pending"),
        created_by=current_user.id,
    )
    db.session.add(gen)
    db.session.commit()

    return jsonify({"success": True, "generation": {"id": gen.id, "status": gen.status}}), 201


@video_bp.route("/generations/<int:gen_id>/status", methods=["GET"])
@login_required
def get_generation_status(gen_id):
    gen = VideoGeneration.query.get_or_404(gen_id)
    # Poll if status is not terminal (completed/failed/cancelled/expired)
    terminal_statuses = {"completed", "failed", "cancelled", "expired"}
    if gen.status not in terminal_statuses and gen.polling_url:
        try:
            status_data = VideoService.poll_status(gen.polling_url)
            current_app.logger.info(f"[OpenRouter] poll_status gen={gen_id} response: {status_data}")
            new_status = status_data.get("status", gen.status)
            if new_status != gen.status:
                gen.status = new_status
            if gen.status == "completed":
                urls = status_data.get("unsigned_urls", [])
                gen.unsigned_url = urls[0] if urls else None
                usage = status_data.get("usage", {})
                gen.cost = usage.get("cost")
                gen.completed_at = datetime.utcnow()
                db.session.commit()
            elif gen.status == "failed":
                gen.error_message = status_data.get("error", status_data.get("error_message"))
                db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Polling error for gen {gen_id}: {e}", exc_info=True)

    return jsonify({
        "success": True,
        "generation": {
            "id": gen.id,
            "status": gen.status,
            "unsigned_url": gen.unsigned_url,
            "drive_file_id": gen.drive_file_id,
            "drive_view_url": gen.drive_view_url,
            "local_path": gen.local_path,
            "error_message": gen.error_message,
            "cost": gen.cost,
            "created_at": gen.created_at.isoformat() if gen.created_at else None,
            "completed_at": gen.completed_at.isoformat() if gen.completed_at else None,
        }
    })


@video_bp.route("/generations/<int:gen_id>/download", methods=["POST"])
@login_required
def download_generation_video(gen_id):
    current_app.logger.info(f"[download] requested for gen_id={gen_id}")
    gen = VideoGeneration.query.get_or_404(gen_id)
    if not _is_assigned_or_admin(gen.scene.episode_id):
        current_app.logger.warning(f"[download] unauthorized for gen_id={gen_id}")
        return jsonify({"success": False, "message": "غير مصرح لك."}), 403
    if gen.status != "completed" or not gen.unsigned_url:
        current_app.logger.warning(f"[download] not ready gen_id={gen_id} status={gen.status} url={gen.unsigned_url}")
        return jsonify({"success": False, "message": "الفيديو غير جاهز."}), 400

    local_path = os.path.join(
        "static", "videos",
        f"episode_{gen.scene.episode_id}",
        f"scene_{gen.scene.number}",
        f"gen_{gen.id}.mp4"
    )
    try:
        current_app.logger.info(f"[download] starting download for gen_id={gen_id} to {local_path}")
        VideoService.download_video(gen.unsigned_url, local_path)
        gen.local_path = local_path
        db.session.commit()
        current_app.logger.info(f"[download] success gen_id={gen_id} path={local_path}")
        return jsonify({"success": True, "local_path": local_path})
    except Exception as e:
        current_app.logger.error(f"Download error for gen {gen_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"خطأ في التحميل: {e}"}), 500


@video_bp.route("/generations/<int:gen_id>/save-to-drive", methods=["POST"])
@login_required
def save_generation_to_drive(gen_id):
    current_app.logger.info(f"[drive] save requested for gen_id={gen_id}")
    gen = VideoGeneration.query.get_or_404(gen_id)
    if not _is_assigned_or_admin(gen.scene.episode_id):
        current_app.logger.warning(f"[drive] unauthorized for gen_id={gen_id}")
        return jsonify({"success": False, "message": "غير مصرح لك."}), 403
    if not gen.local_path or not os.path.exists(gen.local_path):
        current_app.logger.warning(f"[drive] local file missing gen_id={gen_id} path={gen.local_path}")
        return jsonify({"success": False, "message": "الملف المحلي غير موجود."}), 400

    try:
        current_app.logger.info(f"[drive] uploading gen_id={gen_id} from {gen.local_path}")
        drive_file_id, drive_view_url = VideoService.upload_to_drive(
            gen.local_path,
            gen.scene.episode_id,
            gen.scene.episode.title,
            gen.scene.number,
            gen.id,
        )
        gen.drive_file_id = drive_file_id
        gen.drive_view_url = drive_view_url
        # Delete local file after successful upload
        os.remove(gen.local_path)
        gen.local_path = None
        db.session.commit()
        current_app.logger.info(f"[drive] upload success gen_id={gen_id} drive_file_id={drive_file_id}")
        return jsonify({"success": True, "drive_file_id": drive_file_id, "drive_view_url": drive_view_url})
    except Exception as e:
        current_app.logger.error(f"Drive upload error for gen {gen_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"خطأ في الرفع: {e}"}), 500


@video_bp.route("/generations/<int:gen_id>", methods=["DELETE"])
@login_required
def delete_generation(gen_id):
    gen = VideoGeneration.query.get_or_404(gen_id)
    if not _is_assigned_or_admin(gen.scene.episode_id):
        return jsonify({"success": False, "message": "غير مصرح لك."}), 403

    if gen.local_path and os.path.exists(gen.local_path):
        os.remove(gen.local_path)
    if gen.drive_file_id:
        VideoService.delete_from_drive(gen.drive_file_id)

    db.session.delete(gen)
    db.session.commit()
    return jsonify({"success": True, "message": "تم حذف عملية التوليد."})
