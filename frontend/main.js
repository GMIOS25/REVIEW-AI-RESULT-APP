/* global window */

let ALL_RECORDS = [];
let SELECTED_ID = null;
let CURRENT_DETAIL = null;

// Tên hiển thị tiếng Việt cho các field hay gặp - fallback dùng luôn tên field gốc
// nếu không có trong danh sách này (vì schema DB gốc chưa cố định).
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
  id: "ID",
  file_name: "Tên file",
  link: "Liên kết lưu trữ",
};

function fieldLabel(key) {
  return FIELD_LABELS[key] || key;
}

function readonlyLabel(key) {
  return READONLY_LABELS[key] || key;
}

function whenApiReady(callback) {
  if (window.pywebview && window.pywebview.api) {
    callback();
  } else {
    window.addEventListener("pywebviewready", callback, { once: true });
  }
}

function init() {
  whenApiReady(async () => {
    ALL_RECORDS = await window.pywebview.api.get_records();
    renderLedger(ALL_RECORDS);
    renderStats(ALL_RECORDS);
  });

  document.getElementById("search-input").addEventListener("input", onSearch);
  document.getElementById("review-form").addEventListener("submit", onSubmitReview);
}

function renderStats(records) {
  const total = records.length;
  const reviewed = records.filter(r => r.review_status === "reviewed").length;
  document.getElementById("stat-total").textContent = total;
  document.getElementById("stat-reviewed").textContent = reviewed;
  document.getElementById("stat-pending").textContent = total - reviewed;
}

function onSearch(e) {
  const q = e.target.value.trim().toLowerCase();
  if (!q) {
    renderLedger(ALL_RECORDS);
    return;
  }
  const filtered = ALL_RECORDS.filter(r =>
    [r.file_name, r.sender, r.receiver].some(v => (v || "").toLowerCase().includes(q))
  );
  renderLedger(filtered);
}

function renderLedger(records) {
  const body = document.getElementById("ledger-body");
  body.innerHTML = "";

  for (const r of records) {
    const tr = document.createElement("tr");
    tr.dataset.id = r.id;
    if (r.id === SELECTED_ID) tr.classList.add("is-selected");

    const statusChipClass = r.review_status === "reviewed" ? "status-chip--reviewed" : "status-chip--pending";
    const statusText = r.review_status === "reviewed" ? "Đã duyệt" : "Chờ duyệt";

    tr.innerHTML = `
      <td class="col-id">${escapeHtml(r.id)}</td>
      <td>${escapeHtml(r.file_name || "")}</td>
      <td>${escapeHtml(r.sender || "")}</td>
      <td>${escapeHtml(r.receiver || "")}</td>
      <td>${escapeHtml(formatTime(r.time))}</td>
      <td class="col-status"><span class="status-chip ${statusChipClass}">${statusText}</span></td>
    `;
    tr.addEventListener("click", () => selectRecord(r.id));
    body.appendChild(tr);
  }
}

function formatTime(value) {
  if (!value) return "";
  return String(value).replace("T", " ").slice(0, 16);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function selectRecord(id) {
  SELECTED_ID = id;
  document.querySelectorAll("#ledger-body tr").forEach(tr => {
    tr.classList.toggle("is-selected", Number(tr.dataset.id) === Number(id));
  });

  document.getElementById("detail-empty").hidden = true;
  const content = document.getElementById("detail-content");
  content.hidden = false;

  const detail = await window.pywebview.api.get_record_detail(id);
  CURRENT_DETAIL = detail;

  if (detail.error) {
    alert(detail.error);
    return;
  }

  renderReadonlyFields(detail.readonly_fields);
  renderPdf(detail.pdf_base64, detail.pdf_error);
  renderReviewForm(detail.review_fields, detail.existing_review);

  document.getElementById("saved-indicator").hidden = true;
}

function renderReadonlyFields(fields) {
  const el = document.getElementById("readonly-fields");
  el.innerHTML = Object.entries(fields)
    .map(([k, v]) => `<span class="field-name">${escapeHtml(readonlyLabel(k))}:</span>${escapeHtml(v ?? "")}<br>`)
    .join("");
}

function renderPdf(pdfBase64, pdfError) {
  const frame = document.getElementById("pdf-frame");
  const emptyEl = document.getElementById("pdf-empty");

  if (pdfBase64) {
    frame.hidden = false;
    emptyEl.hidden = true;
    frame.src = `data:application/pdf;base64,${pdfBase64}`;
  } else {
    frame.hidden = true;
    emptyEl.hidden = false;
    emptyEl.textContent = pdfError || "Không tìm thấy file PDF liên kết.";
  }
}

function renderReviewForm(reviewFields, existingReview) {
  const container = document.getElementById("review-fields");
  container.innerHTML = "";

  const corrections = existingReview ? existingReview.corrections : {};

  for (const [key, originalValue] of Object.entries(reviewFields)) {
    const hasCorrection = corrections && Object.prototype.hasOwnProperty.call(corrections, key);
    const value = hasCorrection ? corrections[key] : (originalValue ?? "");

    const group = document.createElement("div");
    group.className = "field-group";
    group.innerHTML = `
      <label for="field-${key}">${escapeHtml(fieldLabel(key))}</label>
      <input type="text" id="field-${key}" data-field="${key}"
             data-original="${escapeHtml(originalValue ?? "")}"
             value="${escapeHtml(value)}" class="${hasCorrection ? "is-edited" : ""}">
    `;
    const input = group.querySelector("input");
    input.addEventListener("input", () => {
      input.classList.toggle("is-edited", input.value !== input.dataset.original);
    });
    container.appendChild(group);
  }

  // Khôi phục kết luận & ghi chú nếu đã từng review
  const form = document.getElementById("review-form");
  form.reset();
  document.getElementById("note-input").value = "";

  if (existingReview) {
    const verdictValue = existingReview.is_correct_overall ? "correct" : "incorrect";
    const radio = form.querySelector(`input[name="verdict"][value="${verdictValue}"]`);
    if (radio) radio.checked = true;
    document.getElementById("note-input").value = existingReview.note || "";
  }
}

async function onSubmitReview(e) {
  e.preventDefault();
  if (SELECTED_ID === null) return;

  const form = e.target;
  const verdict = form.querySelector('input[name="verdict"]:checked');
  if (!verdict) {
    alert("Vui lòng chọn kết luận ĐÚNG hoặc SAI trước khi gửi.");
    return;
  }

  const corrections = {};
  document.querySelectorAll("#review-fields input[data-field]").forEach(input => {
    if (input.value !== input.dataset.original) {
      corrections[input.dataset.field] = input.value;
    }
  });

  const note = document.getElementById("note-input").value;
  const isCorrect = verdict.value === "correct";

  const submitBtn = form.querySelector(".btn-submit");
  submitBtn.disabled = true;
  submitBtn.textContent = "Đang gửi...";

  const result = await window.pywebview.api.submit_review(SELECTED_ID, isCorrect, corrections, note);

  submitBtn.disabled = false;
  submitBtn.textContent = "Gửi đánh giá";

  if (!result.ok) {
    alert("Có lỗi khi lưu đánh giá: " + result.error);
    return;
  }

  document.getElementById("saved-indicator").hidden = false;

  // Cập nhật trạng thái trong danh sách bên trái mà không cần gọi lại toàn bộ get_records()
  const rec = ALL_RECORDS.find(r => r.id === SELECTED_ID);
  if (rec) rec.review_status = "reviewed";
  renderLedger(ALL_RECORDS);
  renderStats(ALL_RECORDS);

  const tr = document.querySelector(`#ledger-body tr[data-id="${SELECTED_ID}"]`);
  if (tr) tr.classList.add("is-selected");
}

init();
