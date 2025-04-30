# AWS Lambda function to sync S3 files to Backblaze B2
import os
import json
import boto3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handler(event, context):
    """
    Daily scheduled function to sync all files in S3 bucket to Backblaze B2.
    Creates a replica by comparing etags.
    """
    # Get environment variables from the AWS Parameter Store
    b2_endpoint_url = os.environ.get('B2_ENDPOINT_URL')
    b2_key_id = os.environ.get('B2_APPLICATION_KEY_ID')
    b2_app_key = os.environ.get('B2_APPLICATION_KEY')
    b2_bucket = os.environ.get('B2_BUCKET_NAME')
    source_bucket = os.environ.get('SOURCE_BUCKET_NAME')

    # Log configuration
    logger.info(f"Starting sync from {source_bucket} to B2 bucket {b2_bucket}")
    logger.info(f"Using B2 endpoint: {b2_endpoint_url}")

    # Initialize source S3 client (AWS)
    source_s3 = boto3.client('s3')

    # Initialize destination S3 client (Backblaze B2)
    destination_s3 = boto3.client(
        's3',
        endpoint_url=b2_endpoint_url,
        aws_access_key_id=b2_key_id,
        aws_secret_access_key=b2_app_key,
        config=boto3.session.Config(s3={'payload_signing_enabled': False})
    )

    try:
        # Step 1: Get a list of all objects in the source S3 bucket
        source_objects = {}
        source_paginator = source_s3.get_paginator('list_objects_v2')

        for page in source_paginator.paginate(Bucket=source_bucket):
            if 'Contents' in page:
                for obj in page['Contents']:
                    source_objects[obj['Key']] = obj['ETag'].strip('"')  # Store without quotes

        logger.info(f"Found {len(source_objects)} objects in source bucket")

        # Step 2: Get a list of all objects in the destination B2 bucket
        destination_objects = {}
        destination_paginator = destination_s3.get_paginator('list_objects_v2')

        for page in destination_paginator.paginate(Bucket=b2_bucket):
            if 'Contents' in page:
                for obj in page['Contents']:
                    destination_objects[obj['Key']] = obj['ETag'].strip('"')  # Store without quotes

        logger.info(f"Found {len(destination_objects)} objects in destination bucket")

        # Step 3: Compare and sync
        files_added = 0
        files_updated = 0
        files_deleted = 0

        # Find objects to add or update
        for key, etag in source_objects.items():
            # If object doesn't exist in destination or etag is different, copy it
            if key not in destination_objects or destination_objects[key] != etag:
                try:
                    logger.info(f"Copying file: {key}")

                    # Get file from source
                    response = source_s3.get_object(
                        Bucket=source_bucket,
                        Key=key
                    )
                    file_data = response['Body'].read()

                    # Upload to destination
                    destination_s3.put_object(
                        Bucket=b2_bucket,
                        Key=key,
                        Body=file_data,
                        ContentType=response.get('ContentType', 'application/octet-stream')
                    )

                    if key in destination_objects:
                        files_updated += 1
                        logger.info(f"Updated file: {key}")
                    else:
                        files_added += 1
                        logger.info(f"Added file: {key}")

                except Exception as e:
                    logger.error(f"Error copying file {key}: {str(e)}")

        # Find objects to delete (exist in destination but not in source)
        for key in destination_objects:
            if key not in source_objects:
                try:
                    logger.info(f"Deleting file: {key}")

                    # Delete from destination
                    destination_s3.delete_object(
                        Bucket=b2_bucket,
                        Key=key
                    )

                    files_deleted += 1
                    logger.info(f"Deleted file: {key}")

                except Exception as e:
                    logger.error(f"Error deleting file {key}: {str(e)}")

        # Final report
        logger.info(f"Sync complete. Added: {files_added}, Updated: {files_updated}, Deleted: {files_deleted}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Sync completed successfully',
                'stats': {
                    'added': files_added,
                    'updated': files_updated,
                    'deleted': files_deleted
                }
            })
        }

    except Exception as e:
        logger.error(f"Error during sync process: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error during sync: {str(e)}')
        }
