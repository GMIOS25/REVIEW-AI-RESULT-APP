"""
Provider lấy PDF thật từ AWS S3. CHƯA được dùng ở giai đoạn hiện tại vì chưa có
tài khoản AWS — để sẵn ở đây để khi có credentials chỉ cần:

  1. pip install boto3
  2. Đặt biến môi trường AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (hoặc AWS profile)
  3. Đổi config.STORAGE_PROVIDER = "s3" và điền config.S3_BUCKET_NAME
  4. Không cần sửa gì ở api.py / frontend — vì cùng implement StorageProvider interface.
"""

from app.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    def __init__(self, bucket_name: str, region: str, key_template: str):
        self.bucket_name = bucket_name
        self.region = region
        self.key_template = key_template
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3  # import trễ để không bắt buộc cài boto3 khi chưa dùng S3
            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def _key_for(self, record: dict) -> str:
        return self.key_template.format(**record)

    def pdf_exists(self, record: dict) -> bool:
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=self._key_for(record))
            return True
        except Exception:
            return False

    def get_pdf_bytes(self, record: dict) -> bytes:
        client = self._get_client()
        obj = client.get_object(Bucket=self.bucket_name, Key=self._key_for(record))
        return obj["Body"].read()
