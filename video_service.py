# video_service.py
# Encapsulates OpenRouter video generation and Google Drive upload/download.

import json
import os
import requests
from datetime import datetime, timedelta

# Google Drive imports
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# In-memory cache for video models (TTL 6 hours)
_models_cache = None
_models_cache_timestamp = None
_MODELS_CACHE_TTL = timedelta(hours=6)

# In-memory cache for USD->EUR FX rate (TTL 12 hours)
_fx_cache = None
_fx_cache_timestamp = None
_FX_CACHE_TTL = timedelta(hours=12)
_FX_FALLBACK_RATE = 0.92  # used only if frankfurter.app is unreachable


def _get_openrouter_api_key():
    return os.environ.get("OPENROUTER_API_KEY", "")


def _get_openrouter_management_key():
    # Falls back to inference key if management key not set.
    return os.environ.get("OPENROUTER_MANAGEMENT_KEY") or _get_openrouter_api_key()


def _get_drive_credentials_path():
    return os.environ.get("GOOGLE_DRIVE_CREDENTIALS_PATH", "instance/service-account.json")


def _get_drive_root_folder_name():
    return os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_NAME", "صالح - الكراسة الحمراء 📕")


def _get_oauth_tokens_path():
    return os.environ.get("GOOGLE_DRIVE_OAUTH_TOKENS_PATH", "instance/oauth_tokens.json")


class VideoService:
    @staticmethod
    def _get_headers():
        return {
            "Authorization": f"Bearer {_get_openrouter_api_key()}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _get_management_headers():
        return {
            "Authorization": f"Bearer {_get_openrouter_management_key()}",
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

    # --- Credits & FX ---
    @staticmethod
    def get_usd_to_eur_rate():
        global _fx_cache, _fx_cache_timestamp
        if _fx_cache and _fx_cache_timestamp:
            if datetime.utcnow() - _fx_cache_timestamp < _FX_CACHE_TTL:
                return _fx_cache
        try:
            resp = requests.get(
                "https://api.frankfurter.app/latest",
                params={"from": "USD", "to": "EUR"},
                timeout=10,
            )
            resp.raise_for_status()
            rate = float(resp.json()["rates"]["EUR"])
            _fx_cache = rate
            _fx_cache_timestamp = datetime.utcnow()
            return rate
        except Exception as e:
            print(f"[VideoService] FX fetch failed, using fallback {_FX_FALLBACK_RATE}: {e}")
            return _FX_FALLBACK_RATE

    @staticmethod
    def get_credits():
        url = f"{OPENROUTER_BASE_URL}/credits"
        resp = requests.get(url, headers=VideoService._get_management_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        total = float(data.get("total_credits", 0))
        used = float(data.get("total_usage", 0))
        remaining = max(0.0, total - used)
        rate = VideoService.get_usd_to_eur_rate()
        return {
            "total_credits_usd": total,
            "total_usage_usd": used,
            "remaining_usd": remaining,
            "remaining_eur": remaining * rate,
            "usd_to_eur_rate": rate,
        }

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
        resp = requests.get(
            unsigned_url,
            headers=VideoService._get_headers(),
            stream=True,
            timeout=60,
        )
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_path

    # --- Google Drive ---
    @staticmethod
    def _load_oauth_client_config():
        """Load OAuth client config from the credentials JSON file."""
        creds_path = _get_drive_credentials_path()
        if not os.path.exists(creds_path):
            return None
        with open(creds_path) as f:
            data = json.load(f)
        # Handle both "installed" (desktop) and "web" client types
        return data.get("installed") or data.get("web")

    @staticmethod
    def _load_oauth_credentials():
        """Load OAuth credentials from stored tokens. Returns None if not connected."""
        tokens_path = _get_oauth_tokens_path()
        if not os.path.exists(tokens_path):
            return None
        client_config = VideoService._load_oauth_client_config()
        if not client_config:
            return None
        with open(tokens_path) as f:
            tokens = json.load(f)
        creds = OAuthCredentials(
            None,  # access token will be refreshed
            refresh_token=tokens.get("refresh_token"),
            token_uri=client_config["token_uri"],
            client_id=client_config["client_id"],
            client_secret=client_config["client_secret"],
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        creds.refresh(Request())
        return creds

    @staticmethod
    def _get_drive_service():
        # Try OAuth first
        oauth_creds = VideoService._load_oauth_credentials()
        if oauth_creds:
            print("[VideoService] Using OAuth credentials for Google Drive")
            return build("drive", "v3", credentials=oauth_creds, cache_discovery=False)

        # Fallback to service account
        creds_path = _get_drive_credentials_path()
        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                f"Google Drive credentials file not found: {creds_path}. "
                f"Please connect Google Drive via OAuth or set GOOGLE_DRIVE_CREDENTIALS_PATH."
            )
        # Check if it's a service account file
        with open(creds_path) as f:
            data = json.load(f)
        if data.get("type") == "service_account":
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            print("[VideoService] Using service account credentials for Google Drive")
            return build("drive", "v3", credentials=credentials, cache_discovery=False)

        raise RuntimeError(
            "Google Drive not connected. Please connect via /api/drive/auth first."
        )

    @staticmethod
    def is_drive_connected():
        """Check if Google Drive is connected (OAuth tokens exist)."""
        return os.path.exists(_get_oauth_tokens_path())

    @staticmethod
    def get_oauth_auth_url(redirect_uri):
        """Generate Google OAuth authorization URL."""
        client_config = VideoService._load_oauth_client_config()
        if not client_config:
            raise FileNotFoundError("OAuth client config not found")

        # Build authorization URL manually
        auth_uri = client_config["auth_uri"]
        from urllib.parse import urlencode
        params = {
            "client_id": client_config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": "https://www.googleapis.com/auth/drive",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{auth_uri}?{urlencode(params)}"

    @staticmethod
    def exchange_oauth_code(code, redirect_uri):
        """Exchange authorization code for tokens and save refresh token."""
        client_config = VideoService._load_oauth_client_config()
        if not client_config:
            raise FileNotFoundError("OAuth client config not found")

        token_uri = client_config["token_uri"]
        resp = requests.post(
            token_uri,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_config["client_id"],
                "client_secret": client_config["client_secret"],
            },
            timeout=30,
        )
        resp.raise_for_status()
        tokens = resp.json()

        # Save refresh token
        tokens_path = _get_oauth_tokens_path()
        os.makedirs(os.path.dirname(tokens_path), exist_ok=True)
        with open(tokens_path, "w") as f:
            json.dump({"refresh_token": tokens["refresh_token"]}, f)

        return tokens

    @staticmethod
    def _find_or_create_folder(service, folder_name, parent_id=None):
        # Escape single quotes for Google Drive API query syntax
        safe_name = folder_name.replace("'", "\\'")
        query = f"mimeType='application/vnd.google-apps.folder' and name='{safe_name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        results = (
            service.files()
            .list(
                q=query,
                corpora="allDrives",
                spaces="drive",
                fields="files(id, name, owners, shared)",
                pageSize=10,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        items = results.get("files", [])
        print(f"[VideoService] _find_or_create_folder found {len(items)} items for '{folder_name}' parent={parent_id}")
        for item in items:
            print(f"  - id={item['id']} name={item['name']} shared={item.get('shared')} owners={[o.get('emailAddress') for o in item.get('owners', [])]}")

        if items:
            # Prefer shared/owned-by-others folders over service account's own
            shared_items = [i for i in items if i.get("shared") or any(
                o.get("emailAddress", "").endswith("@gmail.com")
                for o in i.get("owners", [])
            )]
            chosen = shared_items[0] if shared_items else items[0]
            print(f"[VideoService] Chose folder id={chosen['id']} (shared={chosen.get('shared')})")
            return chosen["id"]

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id] if parent_id else [],
        }
        folder = (
            service.files()
            .create(body=metadata, fields="id", supportsAllDrives=True)
            .execute()
        )
        print(f"[VideoService] Created new folder '{folder_name}' id={folder['id']}")
        return folder["id"]

    @staticmethod
    def upload_to_drive(local_path, episode_id, episode_title, scene_number, generation_number):
        service = VideoService._get_drive_service()

        # Build hierarchy
        root_id = VideoService._find_or_create_folder(service, _get_drive_root_folder_name())
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
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )

        drive_file_id = file.get("id")
        drive_view_url = file.get("webViewLink")

        # Make publicly viewable
        permission = {"type": "anyone", "role": "reader"}
        service.permissions().create(
            fileId=drive_file_id,
            body=permission,
            supportsAllDrives=True,
        ).execute()

        return drive_file_id, drive_view_url

    @staticmethod
    def get_drive_file_metadata(file_id):
        service = VideoService._get_drive_service()
        return (
            service.files()
            .get(fileId=file_id, fields="id,size,mimeType,name", supportsAllDrives=True)
            .execute()
        )

    @staticmethod
    def stream_drive_file(file_id, range_header=None):
        """Stream a Drive file via alt=media with optional Range header.
        Returns (iterator, status_code, response_headers, content_length, total_size, mime_type).
        """
        oauth_creds = VideoService._load_oauth_credentials()
        if oauth_creds:
            token = oauth_creds.token
        else:
            # service account fallback
            creds_path = _get_drive_credentials_path()
            with open(creds_path) as f:
                data = json.load(f)
            if data.get("type") != "service_account":
                raise RuntimeError("No usable Drive credentials for streaming.")
            sa_creds = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            sa_creds.refresh(Request())
            token = sa_creds.token

        meta = VideoService.get_drive_file_metadata(file_id)
        total_size = int(meta.get("size", 0))
        mime_type = meta.get("mimeType", "video/mp4")

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
        headers = {"Authorization": f"Bearer {token}"}
        if range_header:
            headers["Range"] = range_header

        upstream = requests.get(url, headers=headers, stream=True, timeout=60)
        upstream.raise_for_status()

        def generate():
            try:
                for chunk in upstream.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        status = upstream.status_code  # 200 or 206
        out_headers = {
            "Content-Type": mime_type,
            "Accept-Ranges": "bytes",
        }
        if "Content-Range" in upstream.headers:
            out_headers["Content-Range"] = upstream.headers["Content-Range"]
        if "Content-Length" in upstream.headers:
            out_headers["Content-Length"] = upstream.headers["Content-Length"]
        elif total_size and not range_header:
            out_headers["Content-Length"] = str(total_size)

        return generate(), status, out_headers

    @staticmethod
    def delete_from_drive(file_id):
        try:
            service = VideoService._get_drive_service()
            service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
            return True
        except Exception as e:
            print(f"[VideoService] Failed to delete drive file {file_id}: {e}")
            return False
