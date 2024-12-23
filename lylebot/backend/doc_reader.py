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


def list_txt_files_excluding_chat_logs(bucket_name):
    """List all .txt files in the S3 bucket, excluding those under 'chat_logs/'."""
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            return [
                content['Key'] for content in response['Contents']
                if content['Key'].endswith('.txt') and not content['Key'].startswith('chat_logs/')
            ]
        return []
    except Exception as e:
        print(f"Error listing .txt files: {e}")
        return []


def download_txt_file(bucket_name, key):
    """Download a .txt file from S3 and return its content."""
    try:
        txt_file = s3_client.get_object(Bucket=bucket_name, Key=key)
        return txt_file['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading .txt file {key}: {e}")
        return None


def main():
    print("Reading all .txt files in the S3 bucket (excluding chat logs)...\n")

    # List all .txt files excluding those in 'chat_logs/'
    txt_files = list_txt_files_excluding_chat_logs(BUCKET_NAME)

    if not txt_files:
        print("No eligible .txt files found.")
        return

    for txt_file in txt_files:
        print(f"Reading .txt file: {txt_file}")
        content = download_txt_file(BUCKET_NAME, txt_file)
        if content:
            print(f"--- Start of {txt_file} ---")
            print(content)
            print(f"--- End of {txt_file} ---\n")


if __name__ == "__main__":
    main()
