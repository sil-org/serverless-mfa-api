# sync_function.py - Lambda function for S3 to B2 sync
import os
import json
import logging
import subprocess
import shutil
import requests
import zipfile
import stat
from pathlib import Path

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
TEMP_DIR = '/tmp/s3-to-b2'
RCLONE_CONFIG_PATH = '/tmp/rclone.conf'
RCLONE_BINARY_PATH = None  # Will be set during installation


def handler(event, context):
    """
    AWS Lambda handler function to sync S3 bucket to Backblaze B2
    """
    logger.info('Starting S3 to B2 sync process')

    try:
        # Get configuration from environment variables
        s3_bucket = os.environ.get('S3_BUCKET')
        s3_path = os.environ.get('S3_PATH', '')
        b2_bucket = os.environ.get('B2_BUCKET')
        b2_path = os.environ.get('B2_PATH', '')
        b2_application_key_id = os.environ.get('B2_APPLICATION_KEY_ID')
        b2_application_key = os.environ.get('B2_APPLICATION_KEY')
        rclone_arguments = os.environ.get('RCLONE_ARGUMENTS', '')

        if not s3_bucket or not b2_bucket or not b2_application_key_id or not b2_application_key:
            raise ValueError('Missing required environment variables')

        # Clean temp directory
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR, exist_ok=True)

        # Download and install rclone
        logger.info('Installing rclone')
        install_rclone()

        # Create rclone config
        logger.info('Creating rclone config')
        create_rclone_config(b2_application_key_id, b2_application_key)

        # Run rclone sync
        logger.info(f"Syncing s3:{s3_bucket}/{s3_path} to b2:{b2_bucket}/{b2_path}")
        rclone_output = run_rclone_sync(s3_bucket, s3_path, b2_bucket, b2_path, rclone_arguments)
        logger.info(f'Sync completed: {rclone_output}')

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Backup completed successfully'})
        }
    except Exception as e:
        logger.error(f'Error during backup: {str(e)}', exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def install_rclone():
    """
    Download and install rclone binary
    """
    # Download rclone zip
    rclone_zip_path = '/tmp/rclone.zip'

    try:
        logger.info('Downloading rclone')
        response = requests.get('https://downloads.rclone.org/rclone-current-linux-amd64.zip', stream=True)
        response.raise_for_status()

        with open(rclone_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info('Extracting rclone')
        with zipfile.ZipFile(rclone_zip_path, 'r') as zip_ref:
            zip_ref.extractall('/tmp')

        # Find extracted folder
        extracted_folder = None
        for item in os.listdir('/tmp'):
            if item.startswith('rclone-'):
                extracted_folder = item
                break

        if not extracted_folder:
            raise Exception('Failed to find extracted rclone folder')

        # Use the rclone binary directly from the extracted folder
        # instead of copying it to avoid "text file busy" errors
        global RCLONE_BINARY_PATH
        RCLONE_BINARY_PATH = f'/tmp/{extracted_folder}/rclone'

        # Make it executable
        os.chmod(RCLONE_BINARY_PATH, os.stat(RCLONE_BINARY_PATH).st_mode | stat.S_IEXEC)

        # Test rclone
        subprocess.run([RCLONE_BINARY_PATH, 'version'], check=True, capture_output=True)
        logger.info('Rclone installed successfully')
    except Exception as e:
        logger.error(f'Error installing rclone: {str(e)}', exc_info=True)
        raise


def create_rclone_config(b2_application_key_id, b2_application_key):
    """
    Create rclone config file
    """
    try:
        config_content = f"""
[s3]
type = s3
provider = AWS
env_auth = true

[b2]
type = b2
account = {b2_application_key_id}
key = {b2_application_key}
"""

        with open(RCLONE_CONFIG_PATH, 'w') as f:
            f.write(config_content)

        # Set secure permissions
        os.chmod(RCLONE_CONFIG_PATH, 0o600)
        logger.info('Rclone config created successfully')
    except Exception as e:
        logger.error(f'Error creating rclone config: {str(e)}', exc_info=True)
        raise


def run_rclone_sync(s3_bucket, s3_path, b2_bucket, b2_path, rclone_arguments=''):
    """
    Run rclone sync command
    """
    try:
        # Build S3 URL - just use the bucket name if path is empty
        s3_url = f"s3:{s3_bucket}"
        if s3_path and s3_path.strip():
            s3_url = f"{s3_url}/{s3_path}"

        # Build B2 URL - just use the bucket name if path is empty
        b2_url = f"b2:{b2_bucket}"
        if b2_path and b2_path.strip():
            b2_url = f"{b2_url}/{b2_path}"

        # Log the exact URLs for debugging
        logger.info(f"Source URL: {s3_url}")
        logger.info(f"Destination URL: {b2_url}")

        cmd = [
            RCLONE_BINARY_PATH,
            "sync",
            s3_url,
            b2_url,
            f"--config={RCLONE_CONFIG_PATH}",
            "--transfers=4",
            "--checkers=8",
            "-v"
        ]

        # Add any custom rclone arguments
        if rclone_arguments:
            cmd.extend(rclone_arguments.split())

        logger.info(f'Running command: {" ".join(cmd)}')
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f'Error running rclone: {e.stderr}')
        raise Exception(f'Rclone command failed: {e.stderr}')
    except Exception as e:
        logger.error(f'Error in run_rclone_sync: {str(e)}', exc_info=True)
        raise


# If the script is run directly (for testing)
if __name__ == "__main__":
    # Configure logging to console for direct execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Call the handler
    result = handler({}, None)
    print(json.dumps(result, indent=2))
