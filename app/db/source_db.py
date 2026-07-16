"""
Truy cập DB GỐC — CHỈ ĐỌC (read-only). Không có hàm INSERT/UPDATE/DELETE nào
ở đây, cố tình, để không ai vô tình ghi đè lên dữ liệu gốc của công ty.

Thiết kế "dynamic": không hard-code tên field, vì schema bảng metadata thật
sự chưa được xác định đầy đủ. Đọc field nào có trong bảng thì hiển thị field đó.

Khi đổi từ SQLite sang Postgres/MySQL/SQL Server thật:
  - Viết class mới (VD: PostgresSourceDB) cùng 3 hàm list_records / get_record / list_fields
  - Đổi lựa chọn ở cuối file (get_source_db) theo config.SOURCE_DB_TYPE
"""

import sqlite3
from app import config


class SQLiteSourceDB:
    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name

    def _connect(self):
        # mode=ro : mở ở chế độ chỉ đọc thật sự ở tầng hệ điều hành/SQLite,
        # phòng trường hợp code sau này lỡ tay thêm câu lệnh ghi.
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def list_fields(self):
        """Trả về danh sách tên cột thực tế có trong bảng."""
        conn = self._connect()
        try:
            cur = conn.execute(f"PRAGMA table_info({self.table_name})")
            return [row["name"] for row in cur.fetchall()]
        finally:
            conn.close()

    def list_records(self):
        """Trả về toàn bộ bản ghi dạng list[dict]."""
        conn = self._connect()
        try:
            cur = conn.execute(f"SELECT * FROM {self.table_name}")
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_record(self, record_id):
        """Trả về 1 bản ghi (dict) theo id, hoặc None nếu không tồn tại."""
        conn = self._connect()
        try:
            cur = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE id = ?", (record_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_source_db():
    """Factory: trả về instance SourceDB tương ứng với config hiện tại."""
    if config.SOURCE_DB_TYPE == "sqlite":
        return SQLiteSourceDB(config.SOURCE_DB_PATH, config.SOURCE_TABLE_NAME)
    raise NotImplementedError(
        f"Chua ho tro SOURCE_DB_TYPE='{config.SOURCE_DB_TYPE}'. "
        f"Them class moi trong app/db/source_db.py."
    )
