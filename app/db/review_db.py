"""
Đọc/ghi DB ĐÁNH GIÁ (review.db) — hoàn toàn tách biệt với DB gốc.
Đây là nơi DUY NHẤT trong app được phép ghi dữ liệu.

Schema bảng `reviews`:
    id                 INTEGER PRIMARY KEY
    source_record_id   TEXT        -- id của bản ghi tương ứng bên DB gốc
    status             TEXT        -- 'pending' | 'reviewed'
    is_correct_overall INTEGER     -- 1 = đúng, 0 = sai, NULL = chưa đánh giá
    corrections         TEXT        -- JSON: {"field_name": "gia_tri_da_sua", ...}
    note               TEXT
    reviewer           TEXT
    created_at         TEXT
    updated_at         TEXT
"""

import json
import sqlite3
from datetime import datetime, timezone

from app import config

_SCHEMA = """
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


def _now():
    return datetime.now(timezone.utc).isoformat()


class ReviewDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        conn = self._connect()
        try:
            conn.execute(_SCHEMA)
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


def get_review_db():
    return ReviewDB(config.REVIEW_DB_PATH)
