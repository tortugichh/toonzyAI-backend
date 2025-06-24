from google.cloud import storage
import os

GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_PROJECT = os.getenv("GCS_PROJECT")

def upload_image_to_gcs(image_bytes: bytes, filename: str) -> str:
    client = storage.Client(project=GCS_PROJECT)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/png")
    # blob.make_public()  # Удалено для совместимости с uniform bucket-level access
    return blob.public_url 