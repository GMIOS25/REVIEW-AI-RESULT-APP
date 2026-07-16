# Công cụ Review Dữ liệu Tài liệu

Ứng dụng desktop đơn giản (1 người dùng, không cần đăng nhập) để đối chiếu
dữ liệu metadata (đã lấy từ DB gốc, chỉ đọc) với file PDF gốc liên kết,
và ghi lại đánh giá vào một DB riêng — dùng làm dữ liệu huấn luyện ML sau này.

Xem đầy đủ bối cảnh & kiến trúc tại [`docs/ke-hoach-du-an.md`](docs/ke-hoach-du-an.md).

## 1. Cài đặt (máy dùng để phát triển)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## 2. Sinh dữ liệu mẫu để chạy thử (tuỳ chọn)

Repo đã kèm sẵn `data/source.db` (160 bản ghi mẫu) và `data/pdfs/` (160 file
PDF mẫu, chữ mô phỏng — không mang ý nghĩa thực tế). Nếu muốn sinh lại:

```bash
python scripts/generate_mock_data.py
```

> Khi có DB gốc thật, **không chạy script này** — chỉ cần trỏ
> `app/config.py -> SOURCE_DB_PATH` tới file DB thật (hoặc đổi
> `SOURCE_DB_TYPE` nếu không phải SQLite, xem mục 5).

## 3. Chạy ứng dụng (chế độ phát triển)

```bash
python -m app.main
```

Cửa sổ desktop sẽ mở, hiển thị danh sách bản ghi bên trái, panel xem PDF
+ form đánh giá bên phải.

## 4. Đóng gói thành 1 file .exe để gửi cho người dùng

```bash
pyinstaller build.spec
```

File kết quả: `dist/ReviewApp.exe`. Gửi nguyên file này cho đồng nghiệp —
họ chỉ cần double-click, không cần cài Python hay bất kỳ thư viện nào.

> Lưu ý: nên đóng gói và test thử trên đúng 1 máy Windows sạch (chưa từng
> cài Python) trước khi gửi chính thức, để chắc chắn WebView2 runtime có sẵn
> (mặc định đã có sẵn trên hầu hết Windows 10/11 cập nhật gần đây).

## 5. Khi chuyển sang dữ liệu thật (DB gốc thật + AWS S3 thật)

Toàn bộ thay đổi chỉ nằm ở `app/config.py`, không cần sửa logic hay giao diện:

- **DB gốc không phải SQLite:** thêm class mới trong `app/db/source_db.py`
  (implement `list_records` / `get_record` / `list_fields`), rồi đổi
  `SOURCE_DB_TYPE` trong config.
- **PDF chuyển sang AWS S3:**
  1. `pip install boto3`
  2. Cấu hình credentials AWS (biến môi trường hoặc AWS profile)
  3. Đổi `STORAGE_PROVIDER = "s3"` và điền `S3_BUCKET_NAME` trong `config.py`

## 6. Cấu trúc thư mục

```
review-app/
├── app/            # Toàn bộ logic backend (Python)
│   ├── main.py     # Điểm khởi chạy - tạo cửa sổ pywebview
│   ├── config.py   # Cấu hình trung tâm
│   ├── api.py      # Cầu nối frontend JS <-> backend Python
│   ├── db/         # Truy cập DB gốc (read-only) & DB đánh giá (đọc/ghi)
│   └── storage/    # Lấy file PDF (local giờ / S3 sau)
├── frontend/       # Giao diện (HTML/CSS/JS thuần)
├── data/           # source.db, review.db, pdfs/ (dữ liệu mẫu)
├── scripts/        # Script sinh dữ liệu mẫu
├── docs/           # Tài liệu kế hoạch dự án
├── requirements.txt
└── build.spec      # Cấu hình đóng gói PyInstaller
```
