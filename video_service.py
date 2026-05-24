# video_service.py
# Encapsulates OpenRouter video generation and Google Drive upload/download.

import os
import requests
from datetime import datetime, timedelta

# Google Drive imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- Configuration ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

GOOGLE_DRIVE_CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_DRIVE_CREDENTIALS_PATH", "instance/service-account.json"
)
GOOGLE_DRIVE_ROOT_FOLDER_NAME = os.environ.get(
    "GOOGLE_DRIVE_ROOT_FOLDER_NAME", "صالح - الكراسة الحمراء 📕"
)

# In-memory cache for video models (TTL 6 hours)
_models_cache = None
_models_cache_timestamp = None
_MODELS_CACHE_TTL = timedelta(hours=6)


class VideoService:
    @staticmethod
    def _get_headers():
        return {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

    # --- Model Discovery (cached) ---
    @staticmethod
    def fetch_models():
        global _models_cache, _models_cache_timestamp
        if _models_cache and _models_cache_timestamp:
            if datetime.utcnow() - _models_cache_timestamp < _MODELS_CACHE_TTL:
                return _models_cache

        url = f"{OPENROUTER_BASE_URL}/videos/models"
        try:
            resp = requests.get(url, headers=VideoService._get_headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            _models_cache = models
            _models_cache_timestamp = datetime.utcnow()
            return models
        except Exception as e:
            print(f"[VideoService] Failed to fetch models: {e}")
            return []

    @staticmethod
    def get_cached_models():
        models = VideoService.fetch_models()
        return models

    # --- Generation ---
    @staticmethod
    def submit_generation(
        prompt, model, resolution=None, aspect_ratio=None, generate_audio=True, duration=None
    ):
        url = f"{OPENROUTER_BASE_URL}/videos"
        payload = {
            "model": model,
            "prompt": prompt,
        }
        if resolution:
            payload["resolution"] = resolution
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if generate_audio is not None:
            payload["generate_audio"] = generate_audio
        if duration:
            payload["duration"] = duration

        resp = requests.post(url, headers=VideoService._get_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"[VideoService] submit_generation response: {data}")
        return data

    @staticmethod
    def poll_status(polling_url):
        resp = requests.get(polling_url, headers=VideoService._get_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        print(f"[VideoService] poll_status response: {data}")
        return data

    @staticmethod
    def download_video(unsigned_url, local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        resp = requests.get(unsigned_url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_path

    # --- Google Drive ---
    @staticmethod
    def _get_drive_service():
        if not os.path.exists(GOOGLE_DRIVE_CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"Google Drive service account file not found: {GOOGLE_DRIVE_CREDENTIALS_PATH}. "
                f"Please set GOOGLE_DRIVE_CREDENTIALS_PATH in your .env file."
            )
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_DRIVE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    @staticmethod
    def _find_or_create_folder(service, folder_name, parent_id=None):
        # Escape single quotes for Google Drive API query syntax
        safe_name = folder_name.replace("'", "\\'")
        query = f"mimeType='application/vnd.google-apps.folder' and name='{safe_name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        items = results.get("files", [])
        if items:
            return items[0]["id"]

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id] if parent_id else [],
        }
        folder = service.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    @staticmethod
    def upload_to_drive(local_path, episode_id, episode_title, scene_number, generation_number):
        service = VideoService._get_drive_service()

        # Build hierarchy
        root_id = VideoService._find_or_create_folder(service, GOOGLE_DRIVE_ROOT_FOLDER_NAME)
        episodes_id = VideoService._find_or_create_folder(service, "Episodes", parent_id=root_id)
        ep_folder_name = f"Episode_{episode_id} - {episode_title}"
        ep_id = VideoService._find_or_create_folder(service, ep_folder_name, parent_id=episodes_id)
        scene_folder_name = f"Scene_{scene_number}"
        scene_id = VideoService._find_or_create_folder(service, scene_folder_name, parent_id=ep_id)

        file_name = f"Generation_{generation_number}.mp4"
        file_metadata = {
            "name": file_name,
            "parents": [scene_id],
        }
        media = MediaFileUpload(local_path, mimetype="video/mp4", resumable=True)
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

        drive_file_id = file.get("id")
        drive_view_url = file.get("webViewLink")

        # Make publicly viewable
        permission = {"type": "anyone", "role": "reader"}
        service.permissions().create(fileId=drive_file_id, body=permission).execute()

        return drive_file_id, drive_view_url

    @staticmethod
    def delete_from_drive(file_id):
        try:
            service = VideoService._get_drive_service()
            service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            print(f"[VideoService] Failed to delete drive file {file_id}: {e}")
            return False
