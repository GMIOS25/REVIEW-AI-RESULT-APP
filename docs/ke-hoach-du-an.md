# Kế hoạch dự án: Công cụ Review Dữ liệu (Desktop App)

## 1. Mục tiêu & phạm vi

Xây dựng một ứng dụng desktop đơn giản chạy trên Windows, dùng cho **1 người dùng nội bộ** để:

1. Xem danh sách các bản ghi metadata đã qua xử lý (đọc từ database gốc — **chỉ đọc, không sửa**). Metadata này ghi lại việc gửi tài liệu PDF đến đúng người (ai gửi, ai nhận, thời gian, thuộc dự án/phòng ban nào...) kèm ghi chú bổ sung.
2. Với mỗi bản ghi, xem song song file PDF gốc liên kết với bản ghi đó để đối chiếu.
3. Nhập đánh giá (đúng/sai, sửa giá trị, ghi chú...) và lưu lại vào **một nơi lưu trữ riêng**, tách biệt hoàn toàn khỏi database gốc. Dữ liệu đánh giá này dùng làm dữ liệu huấn luyện/đánh giá cho mô hình học máy.

**Không nằm trong phạm vi:** xác thực người dùng (authen), phân quyền nhiều người dùng, chỉnh sửa dữ liệu gốc.

## 2. Đối tượng sử dụng

Một đồng nghiệp duy nhất, dùng trên máy cá nhân (Windows). Không cần đăng nhập.

## 3. Ràng buộc & bối cảnh thực tế

| Thành phần          | Hiện trạng                                                                                                                                                                                        | Ghi chú thiết kế                                                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Database gốc        | SQLite, 1 bảng `metadata` do người khác tạo/ghi, chỉ đọc                                                                                                                                          | Chưa có schema cố định — thiết kế đọc **dynamic** (đọc mọi cột có sẵn, không hard-code tên field) để không phải sửa code khi bảng gốc đổi cấu trúc |
| Field cần đối chiếu | Loại trừ các field định danh/kỹ thuật (`id`, `file_name`, `link`); chỉ đánh giá field liên quan nội dung tài liệu (VD: người gửi, người nhận, thời gian, thuộc dự án, chủ đề, phòng ban, ghi chú) | Danh sách loại trừ khai báo tập trung ở `config.py` (`FIELDS_EXCLUDED_FROM_REVIEW`), dễ chỉnh nếu bảng gốc có thêm field kỹ thuật khác             |
| Lưu trữ PDF         | Dự tính AWS S3, hiện chưa có tài khoản                                                                                                                                                            | Giai đoạn 1: mô phỏng bằng thư mục local qua interface `StorageProvider`. Cắm `S3StorageProvider` khi có tài khoản, không đổi code khác            |
| Hạ tầng server      | Hiện tại: chạy độc lập trên máy đồng nghiệp, không có server trung tâm. Có khả năng sau này sẽ cần 1 service/API riêng khi mở rộng                                                                | Backend logic tách lớp `db/` và `storage/` rõ ràng ngay từ đầu — sau này bọc thêm 1 lớp API (FastAPI) mà không phải viết lại phần lõi              |
| Khối lượng dữ liệu  | >150 bản ghi (đã mock 160 bản ghi + 160 PDF để phát triển/test)                                                                                                                                   | Bảng danh sách có ô tìm kiếm theo tên file/người gửi/người nhận; chưa cần phân trang phức tạp ở quy mô này                                         |

## 4. Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────┐
│  Ứng dụng desktop (1 tiến trình, chạy trên máy      │
│  (đồng nghiệp - Windows)                            │
│                                                     │
│  ┌────────────────┐       ┌───────────────────────┐ │
│  │ Frontend       │  JS   │ Backend logic (Python)│ │
│  │ (HTML/CSS/JS   │◄─────►│ - api.py (js_api)     │ │
│  │ trong cửa sổ   │  API  │ - đọc DB gốc (SQLite, │ │
│  │ pywebview)     │       │   read-only, dynamic) │ │
│  │                │       │ - đọc/ghi DB review   │ │
│  │ - Bảng records │       │   (SQLite riêng)      │ │
│  │ - Panel PDF    │       │ - lấy file PDF qua    │ │
│  │ - Form đánh giá│       │   StorageProvider     │ │
│  └────────────────┘       │   (local giờ / S3 sau)│ │
│                           └───────────────────────┘ │
└─────────────────────────────────────────────────────┘
        Đóng gói thành 1 file .exe bằng PyInstaller
```

## 5. Stack công nghệ

| Thành phần        | Công nghệ                                                                                           | Lý do                                                                              |
| ----------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Giao diện desktop | **pywebview**                                                                                       | Cửa sổ desktop thật, dùng HTML/CSS/JS, xem PDF native qua base64 + iframe          |
| Ngôn ngữ backend  | **Python** (stdlib `sqlite3`, không dùng ORM)                                                       | Đơn giản hoá tối đa cho quy mô 1 người dùng; tránh thêm dependency không cần thiết |
| DB gốc            | SQLite hiện tại, đọc dynamic theo cột thực tế                                                       | Dễ thêm adapter Postgres/MySQL/SQL Server sau này                                  |
| DB đánh giá       | SQLite riêng (`review.db`), cột `corrections` dạng JSON                                             | Linh hoạt theo field mà không cần đổi schema mỗi khi bảng gốc đổi                  |
| Lưu trữ PDF       | `StorageProvider` interface: `LocalStorageProvider` (giờ) → `S3StorageProvider` (sau, dùng `boto3`) | Cô lập thay đổi khi có tài khoản S3 thật                                           |
| Đóng gói          | **PyInstaller** (`build.spec`, `--onefile` tương đương, ẩn console)                                 | Xuất 1 file `.exe`, đồng nghiệp double-click, không cần cài gì thêm                |

## 6. Cấu trúc thư mục (đã triển khai)

```
review-app/
├── app/
│   ├── main.py              # Điểm khởi chạy: tạo cửa sổ pywebview
│   ├── config.py             # Đường dẫn DB, storage provider, field loại trừ khỏi review
│   ├── api.py                 # Cầu nối frontend JS <-> backend Python
│   ├── db/
│   │   ├── source_db.py      # Đọc READ-ONLY, dynamic theo schema thực tế
│   │   └── review_db.py      # CRUD bảng `reviews`
│   └── storage/
│       ├── base.py           # Interface StorageProvider
│       ├── local_storage.py  # Provider mô phỏng local (đang dùng)
│       └── s3_storage.py     # Provider S3 thật (stub, sẵn sàng bật khi có tài khoản)
├── frontend/
│   ├── index.html            # Layout: bảng records (trái) + PDF/form (phải)
│   ├── style.css
│   └── main.js
├── data/
│   ├── source.db              # Mock 160 bản ghi (để dev/test — thay bằng DB thật khi có)
│   ├── review.db               # Sinh tự động khi chạy lần đầu
│   └── pdfs/                   # Mock 160 file PDF tương ứng
├── scripts/
│   └── generate_mock_data.py  # Script sinh dữ liệu + PDF mẫu
├── requirements.txt
├── build.spec
├── README.md
└── docs/
    └── ke-hoach-du-an.md       # Tài liệu này
```

## 7. Schema bảng đánh giá (`review.db`) — đã triển khai

```
Bảng: reviews
─────────────────────────────────────────────
id                  INTEGER PRIMARY KEY AUTOINCREMENT
source_record_id    TEXT UNIQUE   -- khoá liên kết tới bản ghi trong DB gốc
status              TEXT           -- 'pending' | 'reviewed'
is_correct_overall  INTEGER        -- 1 = đúng, 0 = sai
corrections         TEXT (JSON)    -- {"sender": "gia_tri_da_sua", ...} - chỉ chứa field bị sửa
note                TEXT
reviewer            TEXT
created_at          TEXT
updated_at          TEXT
```

## 8. Luồng sử dụng (User flow) — đã triển khai

1. Đồng nghiệp mở app (double-click `ReviewApp.exe`).
2. App hiển thị danh sách bản ghi bên trái (ID, tên file, người gửi, người nhận, thời gian, trạng thái).
3. Click 1 bản ghi → bên phải hiện: PDF gốc (trên) + form các field cần đối chiếu, đã loại trừ `id`/`file_name`/`link` (dưới).
4. Người dùng sửa trực tiếp giá trị field nếu sai, chọn kết luận tổng thể ĐÚNG/SAI, ghi chú thêm.
5. Bấm "Gửi đánh giá" → ghi vào `review.db`. Nếu bản ghi đã từng review, mở lại sẽ thấy đúng giá trị đã sửa trước đó.
6. Bảng bên trái cập nhật trạng thái "Đã duyệt" ngay lập tức.

## 9. Giai đoạn phát triển (Roadmap)

**Giai đoạn 1 — Đã hoàn thành trong lần triển khai này:**

- App chạy độc lập, không cần server.
- DB gốc mock (SQLite, 160 bản ghi) + PDF mock (160 file) để phát triển/test.
- Storage PDF mô phỏng bằng thư mục local.
- Review ghi vào SQLite cục bộ, hỗ trợ sửa lại đánh giá cũ.
- Có sẵn `build.spec` để đóng gói `.exe`.

**Giai đoạn 2 — Khi có dữ liệu/hạ tầng thật:**

- Trỏ `SOURCE_DB_PATH` sang DB gốc thật (hoặc viết adapter mới nếu không phải SQLite).
- Bật `S3StorageProvider` khi có tài khoản AWS.
- Nếu cần nhiều người dùng cùng lúc: bọc thêm 1 API service (FastAPI) chạy trên server nội bộ, app desktop trở thành client gọi HTTP.

## 10. Rủi ro & lưu ý

- SQLite phù hợp cho 1 người dùng ghi tuần tự; nếu sau này có ≥2 người review cùng lúc, cần chuyển `review.db` sang DB server thật để tránh xung đột ghi.
- Cần test đóng gói `.exe` trên 1 máy Windows sạch trước khi gửi chính thức, để chắc WebView2 runtime hoạt động đúng.
- Vì schema DB gốc chưa cố định, thiết kế đọc dynamic — nếu sau này bảng gốc đổi tên cột đang dùng để loại trừ khỏi review (`id`, `file_name`, `link`), cần cập nhật lại `FIELDS_EXCLUDED_FROM_REVIEW` trong `config.py`.
