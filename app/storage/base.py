"""
Interface chung cho "nơi lưu file PDF". Mọi provider (local, S3, ...) phải
implement đúng 2 hàm dưới đây để phần còn lại của app không cần biết PDF
đang thật sự nằm ở đâu.
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def get_pdf_bytes(self, record: dict) -> bytes:
        """
        Nhận vào 1 bản ghi (dict, đầy đủ field từ DB gốc) và trả về nội dung
        file PDF dạng bytes. Ném FileNotFoundError nếu không tìm thấy.
        """
        raise NotImplementedError

    @abstractmethod
    def pdf_exists(self, record: dict) -> bool:
        raise NotImplementedError
