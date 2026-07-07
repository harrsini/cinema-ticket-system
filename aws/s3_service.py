"""
aws/s3_service.py
-----------------
Handles all Amazon S3 interactions for CineBot:
  - Uploading PDF tickets to S3
  - Generating pre-signed download URLs

Bucket layout:
    tickets/<booking_id>.pdf

All credentials are read at call-time from environment variables
so that dotenv is guaranteed to have loaded before they are used.
"""

import logging
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Pre-signed URL validity in seconds (default 1 hour)
PRESIGNED_URL_EXPIRY = int(os.getenv("S3_PRESIGNED_URL_EXPIRY", "3600"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cfg():
    """Read config fresh from environment on every call."""
    bucket = os.getenv("S3_BUCKET_NAME")
    if not bucket:
        raise RuntimeError(
            "S3_BUCKET_NAME is not set. Add it to your .env file."
        )
    return {
        "bucket":     bucket,
        "region":     os.getenv("AWS_REGION", "us-east-1"),
        "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    }


def _get_s3_client():
    cfg = _cfg()
    return boto3.client(
        "s3",
        region_name=cfg["region"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
    ), cfg["bucket"]


def _build_object_key(booking_id: str) -> str:
    return f"tickets/{booking_id}.pdf"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_ticket(pdf_bytes: bytes, booking_id: str) -> dict:
    """
    Upload a PDF ticket to S3.

    Returns
    -------
    dict(success, object_key, message)
    """
    object_key = _build_object_key(booking_id)

    try:
        client, bucket = _get_s3_client()

        client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
            # No ServerSideEncryption param — let the bucket's default
            # encryption policy apply (avoids InvalidArgument errors).
        )

        logger.info("Ticket uploaded to S3: s3://%s/%s", bucket, object_key)

        return {
            "success":    True,
            "object_key": object_key,
            "message":    f"Ticket uploaded: {object_key}",
        }

    except (BotoCoreError, ClientError) as exc:
        logger.error("S3 upload failed for booking %s: %s", booking_id, exc)
        print(f"[CineBot S3] upload error: {exc}")
        return {
            "success":    False,
            "object_key": None,
            "message":    f"S3 upload failed: {exc}",
        }
    except RuntimeError as exc:
        logger.error("S3 config error: %s", exc)
        print(f"[CineBot S3] config error: {exc}")
        return {
            "success":    False,
            "object_key": None,
            "message":    str(exc),
        }


def generate_presigned_url(object_key: str, expiry: int = PRESIGNED_URL_EXPIRY) -> dict:
    """
    Generate a pre-signed URL for secure, time-limited ticket download.

    Returns
    -------
    dict(success, url, message)
    """
    try:
        client, bucket = _get_s3_client()

        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expiry,
        )

        logger.info("Pre-signed URL generated for %s (expires %ds)", object_key, expiry)

        return {
            "success": True,
            "url":     url,
            "message": "Pre-signed URL generated successfully.",
        }

    except (BotoCoreError, ClientError) as exc:
        logger.error("Pre-signed URL failed for %s: %s", object_key, exc)
        print(f"[CineBot S3] presign error: {exc}")
        return {
            "success": False,
            "url":     None,
            "message": f"Could not generate download URL: {exc}",
        }
    except RuntimeError as exc:
        logger.error("S3 config error: %s", exc)
        return {
            "success": False,
            "url":     None,
            "message": str(exc),
        }


def upload_ticket_and_get_url(
    pdf_bytes: bytes,
    booking_id: str,
    expiry: int = PRESIGNED_URL_EXPIRY,
) -> dict:
    """
    Upload ticket then immediately return a pre-signed download URL.

    Returns
    -------
    dict(success, object_key, url, message)
    """
    upload_result = upload_ticket(pdf_bytes, booking_id)

    if not upload_result["success"]:
        return {
            "success":    False,
            "object_key": None,
            "url":        None,
            "message":    upload_result["message"],
        }

    url_result = generate_presigned_url(upload_result["object_key"], expiry)

    return {
        "success":    url_result["success"],
        "object_key": upload_result["object_key"],
        "url":        url_result["url"],
        "message":    url_result["message"],
    }
