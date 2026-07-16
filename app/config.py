"""
Cấu hình trung tâm. Khi chuyển sang môi trường thật (DB gốc thật / S3 thật),
CHỈ cần sửa file này — không phải sửa logic ở nơi khác.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ---- DB gốc (READ-ONLY) --------------------------------------------------
# Giai đoạn hiện tại: SQLite. Khi đổi sang Postgres/MySQL/SQL Server, viết thêm
# 1 class mới trong app/db/source_db.py implement cùng interface rồi đổi dòng dưới.
SOURCE_DB_TYPE = "sqlite"
SOURCE_DB_PATH = os.path.join(DATA_DIR, "source.db")
SOURCE_TABLE_NAME = "metadata"

# Các field KHÔNG cần đánh giá (hiển thị nhưng không có ô review) — id định danh,
# metadata kỹ thuật không liên quan nội dung tài liệu.
FIELDS_EXCLUDED_FROM_REVIEW = {"id", "file_name", "link"}

# ---- DB đánh giá (đọc/ghi) ------------------------------------------------
REVIEW_DB_PATH = os.path.join(DATA_DIR, "review.db")

# ---- Lưu trữ PDF -----------------------------------------------------------
# "local" = mô phỏng bằng thư mục cục bộ (giai đoạn hiện tại).
# "s3"    = AWS S3 thật (bật lên khi có tài khoản/credentials).
STORAGE_PROVIDER = "local"
LOCAL_PDF_DIR = os.path.join(DATA_DIR, "pdfs")

# Cấu hình S3 (chỉ dùng khi STORAGE_PROVIDER = "s3")
S3_BUCKET_NAME = os.environ.get("REVIEW_APP_S3_BUCKET", "")
S3_REGION = os.environ.get("REVIEW_APP_S3_REGION", "ap-southeast-1")
# Quy ước tên object trên S3, phải khớp với "link" trong DB gốc hoặc quy ước riêng.
S3_KEY_TEMPLATE = "documents/{file_name}"

# ---- Người đánh giá (chưa có authen, ghi cứng 1 tên) -----------------------
DEFAULT_REVIEWER_NAME = os.environ.get("REVIEW_APP_REVIEWER", "reviewer")

# ---- Cửa sổ ứng dụng --------------------------------------------------------
WINDOW_TITLE = "Cong cu Review Du lieu Tai lieu"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 860
