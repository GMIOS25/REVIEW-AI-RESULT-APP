"""
Script sinh dữ liệu MẪU để phát triển/test ứng dụng, KHÔNG dùng cho production.

Tạo ra:
  - data/source.db      : mô phỏng DB gốc (bảng "metadata"), chỉ dùng để test app
                           đọc read-only. Khi có DB gốc thật, KHÔNG cần chạy script này.
  - data/pdfs/{id}.pdf   : file PDF mô phỏng, nội dung chỉ để có chữ hiển thị lên,
                           không mang ý nghĩa thực tế.

Chạy: python scripts/generate_mock_data.py
"""

import os
import random
import sqlite3
import zlib
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "source.db")
PDF_DIR = os.path.join(DATA_DIR, "pdfs")

NUM_RECORDS = 160

SENDERS = ["Nguyen Van A", "Tran Thi B", "Le Van C", "Pham Thi D", "Hoang Van E"]
RECEIVERS = ["Phong Ke Toan", "Phong Nhan Su", "Phong Ky Thuat", "Ban Giam Doc", "Phong Kinh Doanh"]
DEPARTMENTS = ["Ke Toan", "Nhan Su", "Ky Thuat", "Kinh Doanh", "Hanh Chinh"]
SUBJECTS = [
    "Hop dong hop tac",
    "Bien ban ban giao",
    "De xuat ngan sach",
    "Bao cao tien do",
    "Thong bao noi bo",
    "Quyet dinh bo nhiem",
    "Hoa don thanh toan",
    "Bien ban hop",
]
BELONG = ["Du an X", "Du an Y", "Du an Z", "Van phong chinh", "Chi nhanh HN", "Chi nhanh HCM"]
NOTE_SAMPLES = [
    "Da xac nhan qua email.",
    "Can bo sung chu ky.",
    "Ban nhap, cho duyet lai.",
    "Uu tien xu ly truoc 20/07.",
    "",
    "Lien he lai nguoi gui neu thieu trang.",
]


def make_minimal_pdf(lines):
    """
    Tạo nội dung 1 file PDF hợp lệ, đơn giản, KHÔNG cần thư viện ngoài
    (không có sẵn reportlab/fpdf trong môi trường này).
    Chỉ hỗ trợ text thuần, font Helvetica, đủ dùng để mô phỏng "có chữ hiển thị lên".
    """
    def esc(s):
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    content_lines = []
    y = 780
    for line in lines:
        content_lines.append(f"BT /F1 12 Tf 50 {y} Td ({esc(line)}) Tj ET")
        y -= 20
    content_stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    stream_obj = b"<< /Length %d >>\nstream\n" % len(content_stream) + content_stream + b"\nendstream"
    objects.append(stream_obj)

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode()
    return pdf


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE metadata (
            id INTEGER PRIMARY KEY,
            file_name TEXT,
            link TEXT,
            sender TEXT,
            receiver TEXT,
            time TEXT,
            belong TEXT,
            subject TEXT,
            department TEXT,
            note TEXT
        )
        """
    )

    start_date = datetime(2026, 1, 1)
    rows = []
    for i in range(1, NUM_RECORDS + 1):
        file_name = f"tailieu_{i:04d}.pdf"
        link = f"s3://mock-bucket/documents/{file_name}"
        sender = random.choice(SENDERS)
        receiver = random.choice(RECEIVERS)
        time_val = (start_date + timedelta(days=random.randint(0, 180), hours=random.randint(0, 23))).isoformat()
        belong = random.choice(BELONG)
        subject = random.choice(SUBJECTS)
        department = random.choice(DEPARTMENTS)
        note = random.choice(NOTE_SAMPLES)

        rows.append((i, file_name, link, sender, receiver, time_val, belong, subject, department, note))

        pdf_lines = [
            f"TAI LIEU MAU #{i:04d}",
            "-" * 40,
            f"Tieu de: {subject}",
            f"Nguoi gui: {sender}",
            f"Nguoi nhan: {receiver}",
            f"Thoi gian: {time_val}",
            f"Thuoc du an: {belong}",
            f"Phong ban: {department}",
            "",
            "Noi dung mo phong - khong mang y nghia thuc te.",
            "Dung de doi chieu voi du lieu metadata khi review.",
        ]
        if note:
            pdf_lines.append(f"Ghi chu: {note}")

        pdf_bytes = make_minimal_pdf(pdf_lines)
        with open(os.path.join(PDF_DIR, f"{i}.pdf"), "wb") as f:
            f.write(pdf_bytes)

    cur.executemany(
        "INSERT INTO metadata VALUES (?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    conn.close()

    print(f"Da tao {NUM_RECORDS} ban ghi mau tai: {DB_PATH}")
    print(f"Da tao {NUM_RECORDS} file PDF mau tai: {PDF_DIR}")


if __name__ == "__main__":
    main()
