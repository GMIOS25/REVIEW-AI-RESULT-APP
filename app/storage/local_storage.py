"""
Provider MÔ PHỎNG S3 bằng 1 thư mục local. Dùng cho giai đoạn hiện tại
(chưa có tài khoản AWS). Quy ước đặt tên file: "{id}.pdf" trong LOCAL_PDF_DIR,
GIỐNG với quy ước sẽ dùng trên S3 thật (xem S3_KEY_TEMPLATE trong config.py)
để khi chuyển sang S3StorageProvider không phải đổi logic liên kết.
"""

import os

from app import config
from app.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, pdf_dir: str):
        self.pdf_dir = pdf_dir

    def _path_for(self, record: dict) -> str:
        record_id = record.get("id")
        return os.path.join(self.pdf_dir, f"{record_id}.pdf")

    def pdf_exists(self, record: dict) -> bool:
        return os.path.isfile(self._path_for(record))

    def get_pdf_bytes(self, record: dict) -> bytes:
        path = self._path_for(record)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Khong tim thay PDF cho ban ghi id={record.get('id')} tai {path}")
        with open(path, "rb") as f:
            return f.read()


def get_storage_provider() -> StorageProvider:
    if config.STORAGE_PROVIDER == "local":
        return LocalStorageProvider(config.LOCAL_PDF_DIR)
    if config.STORAGE_PROVIDER == "s3":
        from app.storage.s3_storage import S3StorageProvider
        return S3StorageProvider(config.S3_BUCKET_NAME, config.S3_REGION, config.S3_KEY_TEMPLATE)
    raise NotImplementedError(f"Chua ho tro STORAGE_PROVIDER='{config.STORAGE_PROVIDER}'")
