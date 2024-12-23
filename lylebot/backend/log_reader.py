import boto3
import os

# Environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = "lylebot-bucket"

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

LOG_PREFIX = "chat_logs/"  # S3 directory where chat logs are stored


def list_log_files(bucket_name, prefix):
    """List all log files in the S3 bucket under the given prefix."""
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    if 'Contents' in response:
        return [content['Key'] for content in response['Contents']]
    return []


def download_log_file(bucket_name, key):
    """Download a log file from S3 and return its content."""
    try:
        log_file = s3_client.get_object(Bucket=bucket_name, Key=key)
        return log_file['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading log file {key}: {e}")
        return None


def main():
    print("Reading historical chat logs...\n")

    # List all log files
    log_files = list_log_files(BUCKET_NAME, LOG_PREFIX)

    if not log_files:
        print("No chat logs found.")
        return

    for log_file in log_files:
        print(f"Reading log file: {log_file}")
        content = download_log_file(BUCKET_NAME, log_file)
        if content:
            print(f"--- Start of {log_file} ---")
            print(content)
            print(f"--- End of {log_file} ---\n")


if __name__ == "__main__":
    main()
