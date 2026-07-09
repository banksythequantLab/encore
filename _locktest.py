"""Prove immutability: a locked manifest VERSION cannot be deleted or overwritten."""
import os, datetime
from dotenv import load_dotenv
load_dotenv()
import boto3
from botocore.exceptions import ClientError

kid = os.environ["B2_KEY_ID"]; ak = os.environ["B2_APP_KEY"]
region = os.environ.get("B2_REGION", "us-east-005")
s3 = boto3.client("s3", endpoint_url=f"https://s3.{region}.backblazeb2.com",
                  aws_access_key_id=kid, aws_secret_access_key=ak, region_name=region)
bucket = "filmwriter-sealed"; key = "manifests/immutable-demo.json"

until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
r = s3.put_object(Bucket=bucket, Key=key, Body=b'{"provenance":"sealed","hash":"abc123"}',
                  ObjectLockMode="GOVERNANCE", ObjectLockRetainUntilDate=until)
vid = r.get("VersionId")
print("PUT_OK version=", vid)

try:
    ret = s3.get_object_retention(Bucket=bucket, Key=key, VersionId=vid)["Retention"]
    print("RETENTION:", ret["Mode"], "until", str(ret["RetainUntilDate"])[:19])
except ClientError as e:
    print("RET_ERR:", e.response["Error"].get("Code"))

# permanently delete the locked version WITHOUT bypass -> must be refused
try:
    s3.delete_object(Bucket=bucket, Key=key, VersionId=vid)
    print("VERSION_DELETE_SUCCEEDED (lock NOT enforced)")
except ClientError as e:
    print("VERSION_DELETE_REFUSED:", e.response["Error"].get("Code"))

try:
    b = s3.get_object(Bucket=bucket, Key=key, VersionId=vid)["Body"].read()
    print("STILL_READABLE bytes=", len(b))
except ClientError as e:
    print("READ_ERR:", e.response["Error"].get("Code"))
