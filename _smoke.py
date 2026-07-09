"""Free B2 preflight via genblaze (HeadBucket). No generation spend."""
import os
from dotenv import load_dotenv
load_dotenv()
from genblaze_s3 import S3StorageBackend

bucket = os.environ["B2_BUCKET"]
region = os.environ.get("B2_REGION")
try:
    b = S3StorageBackend.for_backblaze(bucket, region=region)  # preflight=True by default
    print(f"B2_PREFLIGHT_OK bucket={bucket} region={region}")
    # cheap round-trip: write + read + delete a tiny provenance-style object
    key = "genblaze/_healthcheck.txt"
    b.put(key, b"filmwriter-genblaze-healthcheck")
    got = b.get(key)
    print("ROUNDTRIP_OK bytes=", len(got), "content_ok=", got == b"filmwriter-genblaze-healthcheck")
    b.delete(key)
    print("CLEANUP_OK deleted", key)
except Exception as e:
    print("B2_ERROR:", type(e).__name__, str(e)[:300])
