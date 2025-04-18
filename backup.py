import requests
import os
import datetime
import shutil
import logging
import sys
import json # Import json for better error handling
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This allows loading config locally, while PythonAnywhere env vars still take precedence
load_dotenv()

# --- Configuration ---
# Environment variables are checked first (e.g., from PythonAnywhere task settings).
# If not found, it falls back to the second argument (default value).
# The .env file provides values if environment variables are not explicitly set.

DDOWNLOAD_API_KEY = os.environ.get("DDOWNLOAD_API_KEY", "YOUR_DDOWNLOAD_API_KEY")
# Updated default path to 'instance/app.db'
DATABASE_PATH = os.environ.get("DATABASE_PATH", "instance/app.db")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "tmp") # Temporary directory for the backup copy
USER_TYPE = os.environ.get("DDOWNLOAD_USER_TYPE", "prem") # User type for upload ('prem' recommended)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout # Log to standard output, which PythonAnywhere captures
)

# --- Helper Functions ---

def get_upload_details(api_key: str) -> tuple[str | None, str | None]:
    """
    Gets an upload server URL and session ID from the DDownload API v2.

    Args:
        api_key: Your DDownload API key.

    Returns:
        A tuple containing (upload_url, session_id) if successful,
        otherwise (None, None).
    """
    # Use the v2 API endpoint
    api_url = f"https://api-v2.ddownload.com/api/upload/server?key={api_key}"
    logging.info("Requesting upload server and session ID from DDownload API v2...")
    try:
        response = requests.get(api_url, timeout=30) # 30 second timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()
        # Check the response structure based on v2 docs
        if data.get("msg") == "OK" and data.get("result") and data.get("sess_id"):
            upload_url = data["result"]
            session_id = data["sess_id"]
            logging.info(f"Successfully obtained upload URL: {upload_url[:30]}... and session ID.")
            return upload_url, session_id
        else:
            logging.error(f"Failed to get upload details. API Response: {data}")
            return None, None

    except requests.exceptions.RequestException as e:
        logging.error(f"Error requesting upload server: {e}")
        return None, None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response from API: {e}")
        logging.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
        return None, None
    except Exception as e:
        logging.error(f"An unexpected error occurred while getting upload details: {e}")
        return None, None

def upload_file(upload_url: str, session_id: str, user_type: str, file_path: str) -> bool:
    """
    Uploads a file to the specified DDownload upload URL using API v2 parameters.

    Args:
        upload_url: The URL obtained from get_upload_details.
        session_id: The session ID obtained from get_upload_details.
        user_type: The user type ('prem' or other, as required by API).
        file_path: The path to the file to upload.

    Returns:
        True if upload was successful (according to API response), False otherwise.
    """
    # Upload URL does not need the API key according to v2 docs for the POST step
    upload_api_url = upload_url
    file_name = os.path.basename(file_path)
    logging.info(f"Attempting to upload '{file_name}' to DDownload...")

    # Prepare data payload with session ID and user type for v2
    payload = {
        'sess_id': session_id,
        'utyp': user_type
    }

    try:
        with open(file_path, 'rb') as f:
            # Send file as multipart/form-data
            files = {'files[]': (file_name, f)}
            # Send sess_id and utyp in the 'data' part of the request
            response = requests.post(upload_api_url, data=payload, files=files, timeout=300) # 5 minute timeout for upload
            response.raise_for_status()

        data = response.json()
        # Log the raw response data to help with debugging
        logging.info(f"Upload response received (raw JSON): {json.dumps(data)}")

        # Check if the response data is a list and is not empty
        if isinstance(data, list) and len(data) > 0:
            # Assume the first element in the list contains the upload result info
            first_item = data[0]
            # --- FIX START v4 ---
            # Check if the first item is a dictionary.
            # Get file_status, provide default '', strip whitespace, and compare to 'OK'.
            if isinstance(first_item, dict) and first_item.get('file_status', '').strip() == 'OK':
            # --- FIX END v4 ---
                # Consider successful if status is OK. Log filecode if available.
                logging.info(f"Successfully uploaded file. Status: OK, File Code: {first_item.get('filecode', 'N/A')}, File URL: {first_item.get('download', 'N/A')}")
                return True
            else:
                # Status is not 'OK' or item is not a dict
                logging.error(f"Upload response status is not OK or format is unexpected. Response item: {first_item}")
                return False
        # Fallback/Alternative: Check if the response is a dictionary (as previously assumed)
        elif isinstance(data, dict) and data.get("msg") == "OK" and isinstance(data.get("result"), list) and len(data["result"]) > 0:
             file_info = data["result"][0]
             logging.info(f"Successfully uploaded file (dict format). File URL: {file_info.get('download', 'N/A')}, File Code: {file_info.get('filecode', 'N/A')}")
             return True
        # If neither list nor expected dictionary format, log as failure
        else:
            logging.error(f"Upload failed or API response format unexpected. Response: {data}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"Error during file upload request: {e}")
        if hasattr(e, 'response') and e.response is not None:
             # Attempt to log JSON error response if possible, otherwise text
            try:
                error_data = e.response.json()
                logging.error(f"Upload Error Response Content: {json.dumps(error_data)}")
            except json.JSONDecodeError:
                logging.error(f"Upload Error Response Content (non-JSON): {e.response.text}")
        return False
    except FileNotFoundError:
        logging.error(f"Backup file not found at: {file_path}")
        return False
    except json.JSONDecodeError as e:
        # This catches errors if response.json() fails
        logging.error(f"Error decoding JSON response after upload: {e}")
        logging.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
        return False
    except Exception as e:
        # Catch any other unexpected errors during response processing
        logging.error(f"An unexpected error occurred during upload response processing: {e}")
        # Log the type of data that caused the error, if available
        if 'data' in locals():
            logging.error(f"Data type that caused error: {type(data)}, Data: {data}")
        return False

# --- Main Backup Logic ---

def main():
    """
    Main function to perform the database backup and upload using API v2.
    """
    logging.info("--- Starting DDownload Backup Task (API v2) ---")

    # Resolve the absolute path for the database
    # If DATABASE_PATH is relative (like 'instance/app.db'), it's resolved
    # relative to the script's current working directory.
    # Ensure this is the correct behavior for your setup.
    abs_database_path = os.path.abspath(DATABASE_PATH)
    logging.info(f"Attempting to back up database from: {abs_database_path}")


    # 1. Validate Configuration
    if DDOWNLOAD_API_KEY == "YOUR_DDOWNLOAD_API_KEY":
        logging.error("DDownload API Key is not configured. Set DDOWNLOAD_API_KEY in environment or .env file.")
        return

    if not os.path.exists(abs_database_path):
        logging.error(f"Database file not found at resolved path: {abs_database_path}. Check DATABASE_PATH setting and script's working directory.")
        return

    # Use absolute path for backup dir if it's relative like 'tmp'
    abs_backup_dir = os.path.abspath(BACKUP_DIR)
    if not os.path.exists(abs_backup_dir):
        try:
            os.makedirs(abs_backup_dir)
            logging.info(f"Created backup directory: {abs_backup_dir}")
        except OSError as e:
            logging.error(f"Could not create backup directory {abs_backup_dir}: {e}")
            return
    else:
        logging.info(f"Using existing backup directory: {abs_backup_dir}")


    # 2. Create Timestamped Backup Copy
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Use the original DATABASE_PATH to get the base filename
    db_filename = os.path.basename(DATABASE_PATH)
    backup_filename = f"{os.path.splitext(db_filename)[0]}_backup_{timestamp}{os.path.splitext(db_filename)[1]}"
    backup_filepath = os.path.join(abs_backup_dir, backup_filename) # Use absolute path for backup dir

    try:
        logging.info(f"Creating temporary backup copy: {backup_filepath}")
        # Copy from the resolved absolute database path
        shutil.copy2(abs_database_path, backup_filepath) # Use copy2 to preserve metadata
        logging.info("Backup copy created successfully.")
    except Exception as e:
        logging.error(f"Failed to create backup copy: {e}")
        # Clean up potentially partially created backup file
        if os.path.exists(backup_filepath):
             try:
                 os.remove(backup_filepath)
             except OSError:
                 pass # Ignore error during cleanup after another error
        return # Stop if we can't copy the file

    # 3. Get DDownload Upload Details (URL and Session ID)
    upload_url, session_id = get_upload_details(DDOWNLOAD_API_KEY)
    if not upload_url or not session_id:
        logging.error("Failed to get upload URL or session ID. Aborting backup.")
        # Clean up temporary file even if API call fails
        try:
            if os.path.exists(backup_filepath): # Check if file exists before removing
                 os.remove(backup_filepath)
                 logging.info(f"Removed temporary backup file: {backup_filepath}")
        except OSError as e:
            logging.warning(f"Could not remove temporary backup file {backup_filepath}: {e}")
        return

    # 4. Upload the Backup File using API v2 details
    upload_successful = upload_file(upload_url, session_id, USER_TYPE, backup_filepath)

    # 5. Clean Up Temporary Backup File
    try:
        if os.path.exists(backup_filepath): # Check if file exists before removing
            os.remove(backup_filepath)
            logging.info(f"Removed temporary backup file: {backup_filepath}")
    except OSError as e:
        # Log a warning if cleanup fails, but don't treat it as a critical error
        logging.warning(f"Could not remove temporary backup file {backup_filepath}: {e}")

    # 6. Final Status Log
    if upload_successful:
        logging.info("--- DDownload Backup Task (API v2) Completed Successfully ---")
    else:
        logging.error("--- DDownload Backup Task (API v2) Failed ---")

    # --- Placeholder for Cleanup Logic ---
    # TODO: Implement cleanup logic here if/when the delete file API endpoint is known.
    # Requires: list_files(), parse filenames, sort by date, delete_file(file_code)


if __name__ == "__main__":
    main()
