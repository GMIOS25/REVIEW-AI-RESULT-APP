import { useState, useEffect, useMemo } from "react";
import {
  MagnifyingGlass,
  CheckCircle,
  XCircle,
  Clock,
  User,
  Sun,
  Moon,
  FilePdf,
  Database,
  FloppyDisk,
  FolderOpen,
  ArrowCounterClockwise,
  ListBullets,
  Warning
} from "@phosphor-icons/react";

// Tên hiển thị tiếng Việt cho các field trong DB
const FIELD_LABELS = {
  sender: "Người gửi",
  receiver: "Người nhận",
  time: "Thời gian",
  belong: "Thuộc về",
  subject: "Chủ đề",
  department: "Phòng ban",
  note: "Ghi chú gốc",
};

const READONLY_LABELS = {
  id: "ID bản ghi",
  file_name: "Tên file PDF",
  link: "Đường dẫn lưu trữ",
};

function getFieldLabel(key) {
  return FIELD_LABELS[key] || key;
}

function getReadonlyLabel(key) {
  return READONLY_LABELS[key] || key;
}

// Mock API phục vụ cho việc xem trước giao diện trên trình duyệt thông thường
const MOCK_RECORDS = Array.from({ length: 30 }, (_, i) => ({
  id: i + 1,
  file_name: `doc_2026_07_16_file_${1000 + i}.pdf`,
  sender: ["Nguyễn Văn A", "Trần Thị B", "Lê Văn C", "Phạm Văn D"][i % 4],
  receiver: ["Phòng Hành chính", "Phòng Nhân sự", "Ban Giám đốc", "Phòng Kế toán"][i % 4],
  time: `2026-07-16T14:${10 + i}:00`,
  review_status: i < 5 ? "reviewed" : "pending",
}));

const MOCK_DETAILS = {
  record: {
    id: 1,
    file_name: "doc_2026_07_16_file_1000.pdf",
    sender: "Nguyễn Văn A",
    receiver: "Phòng Hành chính",
    time: "2026-07-16T14:10:00",
    belong: "Dự án Chuyển đổi số",
    subject: "Hợp đồng dịch vụ hạ tầng",
    department: "Bộ phận IT",
    note: "Tài liệu đính kèm hóa đơn dịch vụ tháng 6",
    link: "s3://company-vault/documents/doc_2026_07_16_file_1000.pdf",
  },
  readonly_fields: {
    id: 1,
    file_name: "doc_2026_07_16_file_1000.pdf",
    link: "s3://company-vault/documents/doc_2026_07_16_file_1000.pdf",
  },
  review_fields: {
    sender: "Nguyễn Văn A",
    receiver: "Phòng Hành chính",
    time: "2026-07-16T14:10:00",
    belong: "Dự án Chuyển đổi số",
    subject: "Hợp đồng dịch vụ hạ tầng",
    department: "Bộ phận IT",
    note: "Tài liệu đính kèm hóa đơn dịch vụ tháng 6",
  },
  existing_review: null,
  pdf_base64: null, // sẽ hiển thị lỗi file giả định trong môi trường mock
  pdf_error: "Chạy trong môi trường trình duyệt - Không nạp được PDF thật.",
};

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");
  const [records, setRecords] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Chi tiết bản ghi đang chọn
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  
  // Dữ liệu Form nhập liệu
  const [formData, setFormData] = useState({});
  const [originalValues, setOriginalValues] = useState({});
  const [verdict, setVerdict] = useState(null); // 'correct' | 'incorrect' | null
  const [note, setNote] = useState("");
  
  // Trạng thái thao tác form
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Áp dụng theme lên document element
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Khởi tạo và nạp danh sách bản ghi ban đầu
  useEffect(() => {
    const fetchRecords = async () => {
      if (window.pywebview && window.pywebview.api) {
        try {
          const res = await window.pywebview.api.get_records();
          setRecords(res);
        } catch (err) {
          console.error("Lỗi khi nạp dữ liệu từ backend:", err);
        }
      } else {
        // Dự phòng mock dữ liệu
        setRecords(MOCK_RECORDS);
      }
    };

    // Đợi pywebview ready
    if (window.pywebview && window.pywebview.api) {
      fetchRecords();
    } else {
      window.addEventListener("pywebviewready", fetchRecords, { once: true });
      // Nếu sau 1.5 giây vẫn chưa có pywebview (ở môi trường browser thường), nạp mock luôn
      const timer = setTimeout(() => {
        if (!window.pywebview) {
          fetchRecords();
        }
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, []);

  // Lọc danh sách theo Ô Tìm kiếm
  const filteredRecords = useMemo(() => {
    return records.filter((rec) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        (rec.file_name || "").toLowerCase().includes(q) ||
        (rec.sender || "").toLowerCase().includes(q) ||
        (rec.receiver || "").toLowerCase().includes(q) ||
        String(rec.id).includes(q)
      );
    });
  }, [records, searchQuery]);

  // Thống kê số liệu để hiển thị trên Header
  const stats = useMemo(() => {
    return {
      total: records.length,
    };
  }, [records]);

  // Hàm chọn bản ghi
  const handleSelectRecord = async (id) => {
    setSelectedId(id);
    setLoadingDetail(true);
    setDetail(null);
    setSaveSuccess(false);

    if (window.pywebview && window.pywebview.api) {
      try {
        const res = await window.pywebview.api.get_record_detail(id);
        setupDetailData(res);
      } catch (err) {
        alert("Lỗi khi tải chi tiết bản ghi: " + err.message);
      } finally {
        setLoadingDetail(false);
      }
    } else {
      // Giả lập nạp dữ liệu ở local browser
      setTimeout(() => {
        const mockRes = {
          ...MOCK_DETAILS,
          record: { ...MOCK_DETAILS.record, id, file_name: `doc_file_${1000 + id}.pdf` },
          readonly_fields: { ...MOCK_DETAILS.readonly_fields, id, file_name: `doc_file_${1000 + id}.pdf` }
        };
        setupDetailData(mockRes);
        setLoadingDetail(false);
      }, 300);
    }
  };

  // Khởi tạo dữ liệu form từ kết quả API chi tiết
  const setupDetailData = (detailData) => {
    setDetail(detailData);
    
    // Thiết lập các trường review
    const reviewFields = detailData.review_fields || {};
    const existing = detailData.existing_review;
    const corrections = existing ? existing.corrections : {};
    
    const formVals = {};
    const origVals = {};
    
    Object.entries(reviewFields).forEach(([key, val]) => {
      origVals[key] = val ?? "";
      // Nếu đã có đánh giá trước đó, nạp giá trị đã sửa, ngược lại dùng giá trị gốc
      if (corrections && Object.prototype.hasOwnProperty.call(corrections, key)) {
        formVals[key] = corrections[key];
      } else {
        formVals[key] = val ?? "";
      }
    });

    setFormData(formVals);
    setOriginalValues(origVals);
    
    // Thiết lập kết luận tổng thể & ghi chú
    if (existing) {
      setVerdict(existing.is_correct_overall ? "correct" : "incorrect");
      setNote(existing.note || "");
    } else {
      setVerdict(null);
      setNote("");
    }
  };

  // Thay đổi input form
  const handleInputChange = (key, value) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
    if (saveSuccess) setSaveSuccess(false);
  };

  // Reset giá trị của 1 trường về nguyên bản
  const handleResetField = (key) => {
    setFormData((prev) => ({
      ...prev,
      [key]: originalValues[key],
    }));
  };

  // Gửi Form Đánh giá lên Python Backend
  const handleSubmitReview = async (e) => {
    e.preventDefault();
    if (!selectedId) return;
    if (!verdict) {
      alert("Vui lòng chọn kết luận ĐÚNG hoặc SAI trước khi gửi.");
      return;
    }

    // Chỉ lấy các trường có giá trị khác với ban đầu để gửi corrections
    const corrections = {};
    Object.keys(formData).forEach((key) => {
      if (formData[key] !== originalValues[key]) {
        corrections[key] = formData[key];
      }
    });

    const isCorrect = verdict === "correct";
    setIsSubmitting(true);

    if (window.pywebview && window.pywebview.api) {
      try {
        const res = await window.pywebview.api.submit_review(
          selectedId,
          isCorrect,
          corrections,
          note
        );
        if (res.ok) {
          handleSaveSuccess();
        } else {
          alert("Lỗi từ backend: " + res.error);
        }
      } catch (err) {
        alert("Lỗi hệ thống khi lưu: " + err.message);
      } finally {
        setIsSubmitting(false);
      }
    } else {
      // Giả lập lưu thành công ở browser
      setTimeout(() => {
        handleSaveSuccess();
        setIsSubmitting(false);
      }, 500);
    }
  };

  const handleSaveSuccess = () => {
    setSaveSuccess(true);
    // Cập nhật trạng thái hiển thị của dòng trong danh sách local
    setRecords((prev) =>
      prev.map((r) =>
        r.id === selectedId ? { ...r, review_status: "reviewed" } : r
      )
    );
  };

  // Format thời gian hiển thị thân thiện
  const formatDateTime = (val) => {
    if (!val) return "";
    return String(val).replace("T", " ").slice(0, 16);
  };

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="header">
        <div className="brand-section">
          <span className="eyebrow">Dành cho Kỹ sư ML &amp; QA</span>
          <h1 className="title">Đối Chiếu Dữ Liệu &amp; Tài Liệu Gốc</h1>
        </div>

        <div className="header-right">
          {/* Stats Bar */}
          <div className="stats-bar">
            <div className="stat-item" title="Tổng bản ghi cần xử lý">
              <span className="stat-icon total">
                <Database size={16} weight="bold" />
              </span>
              <div className="stat-info">
                <span className="stat-count">{stats.total}</span>
                <span className="stat-label">Tổng bản ghi</span>
              </div>
            </div>
          </div>

          {/* Theme Toggle Button */}
          <button
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            title={theme === "dark" ? "Chuyển sang giao diện Sáng" : "Chuyển sang giao diện Tối"}
          >
            {theme === "dark" ? <Sun size={20} weight="fill" /> : <Moon size={20} weight="fill" />}
          </button>
        </div>
      </header>

      {/* Main Dashboard Workspace */}
      <main className="dashboard">
        {/* Left Sidebar - Record Ledger List */}
        <section className="ledger-sidebar" aria-label="Danh sách tài liệu">
          <div className="search-filter-box">
            {/* Search Input */}
            <div className="search-input-wrapper">
              <MagnifyingGlass size={18} className="search-icon" />
              <input
                type="text"
                placeholder="Tìm file, người gửi, người nhận..."
                className="search-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>


          </div>

          {/* List Component */}
          <div className="ledger-list-wrapper">
            {filteredRecords.length > 0 ? (
              <div className="ledger-list">
                {filteredRecords.map((rec) => (
                  <button
                    key={rec.id}
                    className={`ledger-item ${selectedId === rec.id ? "selected" : ""}`}
                    onClick={() => handleSelectRecord(rec.id)}
                  >
                    <div className="ledger-item-header">
                      <span className="ledger-id">#{rec.id}</span>
                      <span className="ledger-filename" title={rec.file_name}>
                        {rec.file_name}
                      </span>

                    </div>

                    <div className="ledger-item-meta">
                      <span className="meta-field" title={`Người gửi: ${rec.sender || "Chưa rõ"}`}>
                        <User size={12} className="meta-icon" />
                        {rec.sender || "—"}
                      </span>
                      <span className="meta-field" title={`Người nhận: ${rec.receiver || "Chưa rõ"}`}>
                        <FolderOpen size={12} className="meta-icon" />
                        {rec.receiver || "—"}
                      </span>
                      <div className="ledger-time">
                        <Clock size={11} className="meta-icon" />
                        {formatDateTime(rec.time)}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-ledger-state">
                <ListBullets className="empty-icon" />
                <p>Không tìm thấy tài liệu phù hợp</p>
              </div>
            )}
          </div>
        </section>

        {/* Right Content Area - PDF and Form Preview */}
        <section className="detail-area" aria-label="Chi tiết đối chiếu dữ liệu">
          {loadingDetail ? (
            <div className="pdf-loading-state">
              <div className="spinner"></div>
              <p>Đang nạp chi tiết tài liệu...</p>
            </div>
          ) : detail ? (
            <div className="detail-content">
              {/* PDF Preview Subsection */}
              <div className="pdf-panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <FilePdf size={18} weight="fill" style={{ color: "#ef4444" }} />
                    <span>File tài liệu đính kèm</span>
                  </div>
                </div>

                <div className="pdf-viewer-container">
                  {detail.pdf_base64 ? (
                    <iframe
                      className="pdf-frame"
                      src={`data:application/pdf;base64,${detail.pdf_base64}`}
                      title="Xem trước PDF"
                    ></iframe>
                  ) : (
                    <div className="pdf-error-state">
                      <Warning size={36} className="pdf-error-icon" />
                      <p>{detail.pdf_error || "Không tìm thấy hoặc không đọc được file PDF gốc."}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Review & Edit Form Subsection */}
              <div className="form-panel">
                <form onSubmit={handleSubmitReview} style={{ display: "flex", flexDirection: "column", height: "100%" }}>
                  <div className="form-scrollable-area">
                    <div className="form-title-section">
                      <h2 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "4px" }}>
                        Bảng Đối Chiếu Giá Trị
                      </h2>
                      <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                        Kiểm tra chéo nội dung file PDF bên trái và sửa lại nếu kết quả nhận diện sai.
                      </p>
                    </div>

                    {/* Readonly Fields Block */}
                    <div className="readonly-section">
                      <div className="section-label" style={{ marginBottom: "6px" }}>Thông tin lưu trữ</div>
                      {Object.entries(detail.readonly_fields || {}).map(([key, val]) => (
                        <div className="readonly-row" key={key}>
                          <span className="readonly-label">{getReadonlyLabel(key)}:</span>
                          <span className="readonly-value">{val ?? "—"}</span>
                        </div>
                      ))}
                    </div>

                    {/* Dynamic Fields Form Fields */}
                    <div className="review-fields-container">
                      <div className="section-label">Dữ liệu trích xuất từ AI</div>
                      {Object.entries(detail.review_fields || {}).map(([key, originalVal]) => {
                        const currentVal = formData[key] ?? "";
                        const isEdited = currentVal !== (originalVal ?? "");

                        return (
                          <div className="field-group" key={key}>
                            <div className="field-label-wrapper">
                              <label htmlFor={`field-${key}`} className="field-label">
                                {getFieldLabel(key)}
                              </label>
                              {isEdited && (
                                <span className="field-edited-indicator">Đã sửa</span>
                              )}
                            </div>

                            <div className="input-container">
                              <input
                                id={`field-${key}`}
                                type="text"
                                className={`form-input ${isEdited ? "is-edited" : ""}`}
                                value={currentVal}
                                onChange={(e) => handleInputChange(key, e.target.value)}
                              />
                              {isEdited && (
                                <button
                                  type="button"
                                  className="reset-field-btn"
                                  onClick={() => handleResetField(key)}
                                  title="Khôi phục giá trị gốc"
                                >
                                  <ArrowCounterClockwise size={14} />
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Verdict (Correct/Incorrect Overall) Block */}
                    <div className="verdict-section">
                      <span className="section-label">Kết luận chất lượng AI trích xuất</span>
                      <div className="verdict-cards">
                        <button
                          type="button"
                          className={`verdict-card ok-card ${verdict === "correct" ? "selected" : ""}`}
                          onClick={() => {
                            setVerdict("correct");
                            if (saveSuccess) setSaveSuccess(false);
                          }}
                        >
                          <CheckCircle className="verdict-card-icon" weight={verdict === "correct" ? "fill" : "regular"} />
                          <span className="verdict-card-title">ĐÚNG</span>
                          <span className="verdict-card-desc">Tất cả thông tin AI lấy ra khớp 100% tài liệu gốc</span>
                        </button>

                        <button
                          type="button"
                          className={`verdict-card bad-card ${verdict === "incorrect" ? "selected" : ""}`}
                          onClick={() => {
                            setVerdict("incorrect");
                            if (saveSuccess) setSaveSuccess(false);
                          }}
                        >
                          <XCircle className="verdict-card-icon" weight={verdict === "incorrect" ? "fill" : "regular"} />
                          <span className="verdict-card-title">SAI</span>
                          <span className="verdict-card-desc">Có thông tin bị sai/thiếu so với tài liệu gốc</span>
                        </button>
                      </div>
                    </div>

                    {/* Note Textarea Block */}
                    <div className="note-section">
                      <label htmlFor="note-input" className="section-label">
                        Ý kiến / Ghi chú bổ sung
                      </label>
                      <textarea
                        id="note-input"
                        className="note-textarea"
                        placeholder="Nhập ghi chú thêm cho mô hình học máy (nếu có)..."
                        value={note}
                        onChange={(e) => {
                          setNote(e.target.value);
                          if (saveSuccess) setSaveSuccess(false);
                        }}
                      ></textarea>
                    </div>
                  </div>

                  {/* Form Actions Footer */}
                  <div className="form-footer">
                    {saveSuccess && (
                      <span className="saved-indicator">
                        <CheckCircle size={16} weight="fill" />
                        Đã lưu đánh giá thành công
                      </span>
                    )}

                    <button
                      type="submit"
                      className="submit-btn"
                      disabled={isSubmitting || !verdict}
                    >
                      <FloppyDisk size={16} />
                      {isSubmitting ? "Đang gửi dữ liệu..." : "Gửi đánh giá"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          ) : (
            <div className="empty-detail-state">
              <FolderOpen className="empty-detail-illustration" />
              <h3>Chọn tài liệu để kiểm tra</h3>
              <p>Chọn một bản ghi bất kỳ từ thanh danh sách bên trái để đối chiếu dữ liệu trích xuất và tệp PDF gốc.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
