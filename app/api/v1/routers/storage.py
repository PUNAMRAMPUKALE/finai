import os, uuid, mimetypes, boto3
from fastapi import APIRouter, HTTPException, Depends

from app.deps import get_current_user   # ← unified import

router = APIRouter(prefix="/storage", tags=["storage"])

_s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
BUCKET = os.getenv("S3_BUCKET", "")
PREFIX = os.getenv("S3_PREFIX", "pitches/")

@router.post("/sign-upload")
def sign_upload(filename: str, content_type: str, u=Depends(get_current_user)):
    if not BUCKET:
        raise HTTPException(500, "S3 bucket not configured")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf"] or "pdf" not in content_type.lower():
        raise HTTPException(400, "Only PDF uploads are allowed")

    obj_key = f"{PREFIX}{uuid.uuid4().hex}{ext}"
    # Either PUT or POST; PUT is simpler for Fetch/Axios
    url = _s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET, "Key": obj_key, "ContentType": content_type},
        ExpiresIn=600,  # 10 min
    )
    # Return where frontend should PUT, and the key you’ll later save in DB
    return {"upload_url": url, "key": obj_key}