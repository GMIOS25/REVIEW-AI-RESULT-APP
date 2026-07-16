"""
Đọc/ghi DB ĐÁNH GIÁ (review.db) — hoàn toàn tách biệt với DB gốc (source.db).
Đây là nơi DUY NHẤT trong app được phép ghi dữ liệu.

DB này có 2 bảng, dùng cho 2 mục đích khác nhau:

1. `reviews`
    id                 INTEGER PRIMARY KEY
    source_record_id   TEXT        -- id của bản ghi tương ứng bên DB gốc
    status             TEXT        -- 'pending' | 'reviewed'
    is_correct_overall INTEGER     -- 1 = đúng, 0 = sai, NULL = chưa đánh giá
    corrections         TEXT        -- JSON: {"field_name": "gia_tri_da_sua", ...}
                                    --  chỉ chứa các field THỰC SỰ bị sửa (diff),
                                    --  dùng để hiển thị lại đúng giá trị đã sửa
                                    --  khi mở lại bản ghi trên UI.
    note               TEXT
    reviewer           TEXT
    created_at         TEXT
    updated_at         TEXT

2. `metadata_after_modify`
    Bản sao "giống hệt cấu trúc" bảng `metadata` bên source.db, nhưng với
    GIÁ TRỊ ĐÃ ÁP DỤNG CORRECTION (bản ghi đầy đủ, không phải diff). Đây là
    dữ liệu "gốc sau khi đã sửa", dùng trực tiếp cho AI/ML train/eval sau
    này mà không cần tự merge corrections vào record gốc mỗi lần dùng.

    Quan trọng: bảng này CHỈ được ghi/cập nhật khi người dùng thực sự bấm
    "Gửi đánh giá" cho bản ghi đó (tức là luôn đi kèm 1 dòng tương ứng bên
    `reviews`). Bản ghi nào chưa từng được review thì KHÔNG xuất hiện ở
    đây — source.db vẫn luôn là nguồn duy nhất cho các bản ghi chưa review.
    Schema của bảng này được tạo ĐỘNG theo đúng danh sách cột hiện có của
    bảng `metadata` gốc (xem source_db.list_fields()), vì schema gốc chưa
    cố định.
"""

import json
import sqlite3
from datetime import datetime, timezone

from app import config

_SCHEMA_REVIEWS = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_record_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    is_correct_overall INTEGER,
    corrections TEXT,
    note TEXT,
    reviewer TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# Tên bảng "metadata gốc sau khi sửa" — cố tình đặt tên khác `metadata` để
# không bao giờ nhầm lẫn với bảng gốc bên source.db (2 file .db khác nhau).
AFTER_MODIFY_TABLE = "metadata_after_modify"


def _now():
    return datetime.now(timezone.utc).isoformat()


class ReviewDB:
    def __init__(self, db_path: str, source_fields=None):
        """
        source_fields: danh sách tên cột thực tế của bảng `metadata` bên
        source.db (lấy từ SourceDB.list_fields()). Dùng để tạo bảng
        `metadata_after_modify` với đúng cấu trúc cột hiện tại của DB gốc.
        Có thể để None nếu chỉ cần dùng bảng `reviews` (bảng
        metadata_after_modify sẽ được tạo/mở rộng cột tự động ở lần
        upsert_metadata_after_modify() đầu tiên).
        """
        self.db_path = db_path
        self._ensure_schema()
        if source_fields:
            self._ensure_after_modify_schema(source_fields)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        conn = self._connect()
        try:
            conn.execute(_SCHEMA_REVIEWS)
            conn.commit()
        finally:
            conn.close()

    def _ensure_after_modify_schema(self, fields):
        """
        Tạo bảng `metadata_after_modify` nếu chưa có, với cột "id" làm khoá
        chính (TEXT, để khớp kiểu so sánh source_record_id dùng str() ở
        khắp nơi trong file này) cộng thêm mọi cột khác của bảng metadata
        gốc, đều khai báo TEXT (an toàn cho mọi kiểu giá trị, vì corrections
        nhập từ UI cũng luôn là chuỗi). Nếu bảng gốc phát sinh thêm cột mới
        sau này mà bảng này đã tồn tại, các cột thiếu sẽ được ALTER TABLE
        thêm vào (không xoá dữ liệu cũ).
        """
        fields = list(fields)
        if "id" not in fields:
            fields = ["id"] + fields

        conn = self._connect()
        try:
            other_cols_sql = ", ".join(
                f'"{f}" TEXT' for f in fields if f != "id"
            )
            create_sql = f'''
                CREATE TABLE IF NOT EXISTS {AFTER_MODIFY_TABLE} (
                    id TEXT PRIMARY KEY,
                    {other_cols_sql},
                    reviewed_at TEXT
                );
            '''
            conn.execute(create_sql)

            existing_cols = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({AFTER_MODIFY_TABLE})")
            }
            for f in fields:
                if f != "id" and f not in existing_cols:
                    conn.execute(f'ALTER TABLE {AFTER_MODIFY_TABLE} ADD COLUMN "{f}" TEXT')

            conn.commit()
        finally:
            conn.close()

    def get_review(self, source_record_id):
        """Trả về review hiện có của 1 bản ghi (dict) hoặc None nếu chưa review."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM reviews WHERE source_record_id = ?",
                (str(source_record_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["corrections"] = json.loads(result["corrections"] or "{}")
            return result
        finally:
            conn.close()

    def list_reviews(self):
        """Trả về dict {source_record_id: status} để hiển thị nhanh trên bảng danh sách."""
        conn = self._connect()
        try:
            cur = conn.execute("SELECT source_record_id, status FROM reviews")
            return {row["source_record_id"]: row["status"] for row in cur.fetchall()}
        finally:
            conn.close()

    def upsert_review(self, source_record_id, is_correct_overall, corrections, note, reviewer=None):
        """Tạo mới hoặc cập nhật review cho 1 bản ghi."""
        reviewer = reviewer or config.DEFAULT_REVIEWER_NAME
        corrections_json = json.dumps(corrections or {}, ensure_ascii=False)
        now = _now()

        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT id FROM reviews WHERE source_record_id = ?",
                (str(source_record_id),),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE reviews
                    SET status = 'reviewed',
                        is_correct_overall = ?,
                        corrections = ?,
                        note = ?,
                        reviewer = ?,
                        updated_at = ?
                    WHERE source_record_id = ?
                    """,
                    (
                        int(bool(is_correct_overall)),
                        corrections_json,
                        note,
                        reviewer,
                        now,
                        str(source_record_id),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO reviews
                        (source_record_id, status, is_correct_overall, corrections, note, reviewer, created_at, updated_at)
                    VALUES (?, 'reviewed', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(source_record_id),
                        int(bool(is_correct_overall)),
                        corrections_json,
                        note,
                        reviewer,
                        now,
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        return self.get_review(source_record_id)

    # ------------------------------------------------------------------ #
    # Bảng `metadata_after_modify` — "bản gốc sau khi sửa", dùng cho ML.
    # Chỉ được gọi từ Api.submit_review(), tức là chỉ ghi khi người dùng
    # thực sự bấm "Gửi đánh giá". Không có nút/luồng nào khác gọi tới đây.
    # ------------------------------------------------------------------ #
    def upsert_metadata_after_modify(self, merged_record: dict):
        """
        merged_record: bản ghi ĐẦY ĐỦ (toàn bộ cột của metadata gốc), trong
        đó các field bị sửa đã được thay bằng giá trị mới từ corrections.
        Ghi đè (insert hoặc update) đúng 1 dòng theo id.
        """
        record_id = merged_record.get("id")
        if record_id is None:
            raise ValueError("merged_record can co field 'id' de ghi vao metadata_after_modify")

        fields = list(merged_record.keys())
        # Đảm bảo schema có đủ cột trước khi ghi (phòng trường hợp ReviewDB
        # được khởi tạo mà không truyền source_fields, hoặc source_db có
        # thêm cột mới từ sau lần tạo bảng đầu tiên).
        self._ensure_after_modify_schema(fields)

        now = _now()
        columns = [f for f in fields if f != "id"]
        col_names_sql = ", ".join(f'"{c}"' for c in columns)
        placeholders_sql = ", ".join("?" for _ in columns)
        update_sql = ", ".join(f'"{c}" = excluded."{c}"' for c in columns)

        conn = self._connect()
        try:
            conn.execute(
                f'''
                INSERT INTO {AFTER_MODIFY_TABLE} (id, {col_names_sql}, reviewed_at)
                VALUES (?, {placeholders_sql}, ?)
                ON CONFLICT(id) DO UPDATE SET
                    {update_sql},
                    reviewed_at = excluded.reviewed_at
                ''',
                [str(record_id)] + [merged_record.get(c) for c in columns] + [now],
            )
            conn.commit()
        finally:
            conn.close()

        return self.get_metadata_after_modify(record_id)

    def get_metadata_after_modify(self, record_id):
        """Trả về bản ghi 'gốc sau khi sửa' (dict) hoặc None nếu chưa từng review."""
        conn = self._connect()
        try:
            cur = conn.execute(
                f"SELECT * FROM {AFTER_MODIFY_TABLE} WHERE id = ?",
                (str(record_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_review_db(source_fields=None):
    return ReviewDB(config.REVIEW_DB_PATH, source_fields=source_fields)
