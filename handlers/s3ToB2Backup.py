# AWS Lambda function to backup S3 files to Backblaze B2
import os
import json
import boto3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handler(event, context):
    """
    Daily scheduled function to backup all files in S3 bucket to Backblaze B2.
    """
    # Get environment variables from the AWS Parameter Store
    b2_endpoint_url = os.environ.get('B2_ENDPOINT_URL')
    b2_key_id = os.environ.get('B2_APPLICATION_KEY_ID')
    b2_app_key = os.environ.get('B2_APPLICATION_KEY')
    b2_bucket = os.environ.get('B2_BUCKET_NAME')
    source_bucket = os.environ.get('SOURCE_BUCKET_NAME')

    # Log configuration
    logger.info(f"Starting backup from {source_bucket} to B2 bucket {b2_bucket}")
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

    files_processed = 0

    try:
        # List all objects in source bucket
        paginator = source_s3.get_paginator('list_objects_v2')

        # Process each page of results
        for page in paginator.paginate(Bucket=source_bucket):
            if 'Contents' not in page:
                logger.info(f"No contents found in this page of results")
                continue

            logger.info(f"Processing page with {len(page['Contents'])} objects")

            # Process each object in the bucket
            for obj in page['Contents']:
                object_key = obj['Key']

                logger.info(f"Processing: {object_key}")

                try:
                    # Download from source S3
                    response = source_s3.get_object(
                        Bucket=source_bucket,
                        Key=object_key
                    )
                    file_data = response['Body'].read()

                    # Upload to destination B2 bucket
                    destination_s3.put_object(
                        Bucket=b2_bucket,
                        Key=object_key,
                        Body=file_data,
                        ContentType=response.get('ContentType', 'application/octet-stream')
                    )

                    logger.info(f"Successfully backed up: {object_key}")
                    files_processed += 1
                except Exception as file_error:
                    # Log error but continue with other files
                    logger.error(f"Error processing file {object_key}: {str(file_error)}")

        logger.info(f"Backup complete. Processed {files_processed} files.")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Backup completed successfully. Processed: {files_processed} files')
        }

    except Exception as e:
        logger.error(f"Error during backup process: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error during backup: {str(e)}')
        }
