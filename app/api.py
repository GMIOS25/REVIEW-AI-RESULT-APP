"""
Class Api — cầu nối duy nhất giữa frontend (JS trong cửa sổ pywebview) và
backend logic (Python). Frontend gọi qua window.pywebview.api.<ten_ham>(...).

Mọi hàm trả về đều phải là kiểu dữ liệu serialize được sang JSON
(dict, list, str, số, bool, None) vì pywebview tự chuyển đổi qua lại.
"""

import base64

from app import config
from app.db.source_db import get_source_db
from app.db.review_db import get_review_db
from app.storage.local_storage import get_storage_provider


class Api:
    def __init__(self):
        self.source_db = get_source_db()
        self.review_db = get_review_db()
        self.storage = get_storage_provider()

    # ------------------------------------------------------------------ #
    # Danh sách bản ghi (bảng bên trái)
    # ------------------------------------------------------------------ #
    def get_records(self):
        """
        Trả về danh sách rút gọn các bản ghi + trạng thái review, dùng để
        render bảng danh sách. Không kèm toàn bộ field để bảng gọn nhẹ.
        """
        records = self.source_db.list_records()
        review_status = self.review_db.list_reviews()

        result = []
        for r in records:
            record_id = r.get("id")
            result.append({
                "id": record_id,
                "file_name": r.get("file_name"),
                "sender": r.get("sender"),
                "receiver": r.get("receiver"),
                "time": r.get("time"),
                "review_status": review_status.get(str(record_id), "pending"),
            })
        return result

    # ------------------------------------------------------------------ #
    # Chi tiết 1 bản ghi (khi click chọn dòng)
    # ------------------------------------------------------------------ #
    def get_record_detail(self, record_id):
        record = self.source_db.get_record(record_id)
        if record is None:
            return {"error": f"Khong tim thay ban ghi id={record_id}"}

        existing_review = self.review_db.get_review(record_id)

        # Tách field nào được phép review, field nào chỉ hiển thị (readonly)
        review_fields = {
            k: v for k, v in record.items()
            if k not in config.FIELDS_EXCLUDED_FROM_REVIEW
        }
        readonly_fields = {
            k: v for k, v in record.items()
            if k in config.FIELDS_EXCLUDED_FROM_REVIEW
        }

        pdf_base64 = None
        pdf_error = None
        try:
            pdf_bytes = self.storage.get_pdf_bytes(record)
            pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
        except FileNotFoundError as e:
            pdf_error = str(e)

        return {
            "record": record,
            "readonly_fields": readonly_fields,
            "review_fields": review_fields,
            "existing_review": existing_review,
            "pdf_base64": pdf_base64,
            "pdf_error": pdf_error,
        }

    # ------------------------------------------------------------------ #
    # Gửi đánh giá
    # ------------------------------------------------------------------ #
    def submit_review(self, record_id, is_correct_overall, corrections, note):
        """
        corrections: dict {field_name: gia_tri_da_sua} — chỉ cần chứa các field
        mà người dùng thực sự sửa, không cần gửi toàn bộ.
        """
        try:
            updated = self.review_db.upsert_review(
                source_record_id=record_id,
                is_correct_overall=is_correct_overall,
                corrections=corrections,
                note=note,
            )
            return {"ok": True, "review": updated}
        except Exception as e:
            return {"ok": False, "error": str(e)}
