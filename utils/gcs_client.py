from google.cloud import storage
import os
from typing import Union
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# If GCS variables are not provided we fall back to local storage so the app
# keeps working in a standalone Docker-Compose without Google credentials.
GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_PROJECT = os.getenv("GCS_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")


def upload_image_to_gcs(image_bytes: bytes, filename: str) -> str:
    """Upload image bytes to GCS and return public URL."""
    print("GCS_BUCKET inside upload_image_to_gcs:", GCS_BUCKET)
    print("GCS_PROJECT inside upload_image_to_gcs:", GCS_PROJECT)
    
    if not GCS_BUCKET:
        raise ValueError("GCS_BUCKET environment variable is not set")
    if not GCS_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")
    
    client = storage.Client(project=GCS_PROJECT)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/png")
    
    # Try to make public, but handle exceptions gracefully
    try:
        blob.make_public()
        print(f"Successfully made blob {filename} public")
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET}/{filename}"
    except Exception as e:
        print(f"Warning: Could not make blob {filename} public: {e}")
        print("This is normal with uniform bucket-level access enabled")
        # Use signed URL for access since public ACL is not available
        public_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),  # 7 days expiration
            method="GET"
        )
        print(f"Generated signed URL instead: {public_url[:100]}...")
    
    print(f"Final URL: {public_url[:100]}...")
    return public_url 


async def upload_file_to_gcs(file_path: str, destination_filename: str) -> str:
    """
    Upload a file to GCS and return the GCS URL.
    
    Args:
        file_path: Local path to the file
        destination_filename: Destination path in GCS bucket
        
    Returns:
        GCS URL (gs://) format
    """
    if not GCS_BUCKET:
        raise ValueError("GCS_BUCKET environment variable is not set")
    if not GCS_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")

    client = storage.Client(project=GCS_PROJECT)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(destination_filename)

    # Determine content type based on file extension
    if file_path.endswith(('.mp4', '.avi', '.mov')):
        content_type = 'video/mp4'
    elif file_path.endswith(('.jpg', '.jpeg', '.png')):
        content_type = 'image/jpeg' if file_path.endswith(('.jpg', '.jpeg')) else 'image/png'
    else:
        content_type = 'application/octet-stream'

    blob.upload_from_filename(file_path, content_type=content_type)

    return f"gs://{GCS_BUCKET}/{destination_filename}"


async def download_file_from_gcs(gcs_url: str, local_path: str) -> None:
    """
    Download a file from GCS to local path.
    
    Args:
        gcs_url: GCS URL in format gs://bucket/path or https://... 
        local_path: Local destination path
    """
    if not GCS_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")

    client = storage.Client(project=GCS_PROJECT)

    # Parse GCS URL
    if gcs_url.startswith("gs://"):
        parts = gcs_url[5:].split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""
    else:
        bucket_name = GCS_BUCKET
        blob_name = gcs_url.split("/")[-1]

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)


def get_public_url(gcs_url: str) -> str:
    """
    Convert GCS URL to public URL if needed.
    
    Args:
        gcs_url: GCS URL in gs:// format
        
    Returns:
        Public HTTP URL
    """
    if gcs_url.startswith("gs://"):
        # Convert gs://bucket/path to public URL
        parts = gcs_url[5:].split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    
    return gcs_url  # Already a public URL


async def download_file_from_gcs_authenticated(gcs_url: str) -> bytes:
    """
    Download file from GCS using authenticated access.
    
    Args:
        gcs_url: GCS URL in gs:// format
        
    Returns:
        File content as bytes
    """
    import asyncio
    import functools
    
    def _download_sync(gcs_url: str) -> bytes:
        try:
            if not GCS_PROJECT:
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")
            client = storage.Client(project=GCS_PROJECT)
            
            # Parse GCS URL
            if gcs_url.startswith("gs://"):
                # Format: gs://bucket/path
                parts = gcs_url[5:].split("/", 1)
                bucket_name = parts[0]
                blob_name = parts[1] if len(parts) > 1 else ""
            else:
                # Fallback for public URLs
                bucket_name = GCS_BUCKET
                blob_name = gcs_url.split("/")[-1]
            
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Check if blob exists
            if not blob.exists():
                raise FileNotFoundError(f"File not found: {gcs_url}")
            
            # Download file content
            return blob.download_as_bytes()
            
        except Exception as e:
            raise Exception(f"Failed to download from GCS: {e}")
    
    # Run sync function in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_sync, gcs_url)


async def get_file_size_from_gcs(gcs_url: str) -> int:
    """
    Get file size from GCS without downloading the file.
    
    Args:
        gcs_url: GCS URL in gs:// format
        
    Returns:
        File size in bytes
    """
    import asyncio
    import functools
    
    def _get_size_sync(gcs_url: str) -> int:
        try:
            if not GCS_PROJECT:
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")
            client = storage.Client(project=GCS_PROJECT)
            
            # Parse GCS URL
            if gcs_url.startswith("gs://"):
                parts = gcs_url[5:].split("/", 1)
                bucket_name = parts[0]
                blob_name = parts[1] if len(parts) > 1 else ""
            else:
                bucket_name = GCS_BUCKET
                blob_name = gcs_url.split("/")[-1]
            
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Reload blob to get metadata
            blob.reload()
            
            return blob.size or 0
            
        except Exception as e:
            raise Exception(f"Failed to get file size from GCS: {e}")
    
    # Run sync function in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_size_sync, gcs_url)


def generate_signed_url(gcs_url: str, expiration_hours: int = 24) -> str:
    """
    Generate a signed URL for temporary access to a GCS file.
    
    Args:
        gcs_url: GCS URL in gs:// format
        expiration_hours: URL expiration time in hours (default: 24)
        
    Returns:
        Signed URL for temporary access
    """
    try:
        client = storage.Client(project=GCS_PROJECT)
        
        # Parse GCS URL
        if gcs_url.startswith("gs://"):
            parts = gcs_url[5:].split("/", 1)
            bucket_name = parts[0]
            blob_name = parts[1] if len(parts) > 1 else ""
        else:
            # Fallback for public URLs
            bucket_name = GCS_BUCKET
            blob_name = gcs_url.split("/")[-1]
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Generate signed URL with expiration
        signed_url = blob.generate_signed_url(
            expiration=datetime.utcnow() + timedelta(hours=expiration_hours),
            method="GET",
            version="v4"
        )
        
        return signed_url
        
    except Exception as e:
        raise Exception(f"Failed to generate signed URL: {e}")


async def generate_signed_url_async(gcs_url: str, expiration_hours: int = 24) -> str:
    """
    Async wrapper for generate_signed_url.
    
    Args:
        gcs_url: GCS URL in gs:// format
        expiration_hours: URL expiration time in hours (default: 24)
        
    Returns:
        Signed URL for temporary access
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_signed_url, gcs_url, expiration_hours) 