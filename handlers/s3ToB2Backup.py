#
# AWS Lambda function to backup S3 files to Backblaze
#
import os
import json
import boto3
import logging
from datetime import datetime, timedelta

# Config for logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """
    Daily scheduled function to backup all files in S3 bucket to Backblaze B2.
    """
    # Initialize source S3 client (AWS)
    source_s3 = boto3.client('s3')

    # Initialize destination S3 client (Backblaze B2)
    destination_s3 = boto3.client(
        's3',
        endpoint_url=os.environ.get('B2_ENDPOINT_URL'),
        aws_access_key_id=os.environ.get('B2_APPLICATION_KEY_ID'),
        aws_secret_access_key=os.environ.get('B2_APPLICATION_KEY'),
        # Downgrade checksum behavior as recommended by Backblaze
        config=boto3.session.Config(s3={'payload_signing_enabled': False})
    )

    # Get bucket names from environment variables
    source_bucket = os.environ.get('SOURCE_BUCKET_NAME')
    destination_bucket = os.environ.get('B2_BUCKET_NAME')

    # Calculate yesterday's date for filtering (optional)
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    files_processed = 0
    files_skipped = 0

    try:
        # List all objects in source bucket
        paginator = source_s3.get_paginator('list_objects_v2')

        # Process each page of results
        for page in paginator.paginate(Bucket=source_bucket):
            if 'Contents' not in page:
                continue

            # Process each object in the bucket
            for obj in page['Contents']:
                object_key = obj['Key']
                last_modified = obj['LastModified']

                # Optional: Only process files modified in the last day
                # Remove this condition if you want to process all files
                if last_modified.strftime('%Y-%m-%d') >= yesterday_str:
                    logger.info(f"Processing: {source_bucket}/{object_key}")

                    # Download from source S3
                    response = source_s3.get_object(
                        Bucket=source_bucket,
                        Key=object_key
                    )
                    file_data = response['Body'].read()

                    # Upload to destination B2 bucket
                    destination_s3.put_object(
                        Bucket=destination_bucket,
                        Key=object_key,
                        Body=file_data,
                        ContentType=response.get('ContentType', 'application/octet-stream')
                    )

                    logger.info(f"Successfully backed up: {object_key}")
                    files_processed += 1
                else:
                    files_skipped += 1

        return {
            'statusCode': 200,
            'body': json.dumps(f'Backup completed successfully. Processed: {files_processed}, Skipped: {files_skipped}')
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error during backup: {str(e)}')
        }
