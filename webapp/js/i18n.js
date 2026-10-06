/**
 * i18n.js -- Từ điển bản địa hoá (Tiếng Việt mặc định, Tiếng Anh dự phòng).
 */

const DICTIONARY = {
  vi: {
    app_title: "Chữ viết tay của bạn",
    app_subtitle: "Biến văn bản thành chữ viết tay tự nhiên của chính bạn",
    tab_write: "Viết chữ",
    tab_teach: "Dạy chữ",
    tab_bank: "Kho mẫu",
    status_ready: "Sẵn sàng",
    status_loading: "Đang tải...",
    status_saving: "Đang lưu kho...",
    status_saved: "Đã lưu vào trình duyệt",
    status_syncing: "Đang đồng bộ đa tab...",
    btn_save: "Lưu",
    btn_clear: "Xoá nét",
    btn_undo: "Hoàn tác",
    btn_export: "Xuất file .xopp",
    btn_backup: "Sao lưu kho (.json.gz)",
    btn_import_bank: "Nhập kho mẫu",
    btn_create_empty: "Tạo kho mới",
    input_placeholder: "Nhập văn bản của bạn vào đây...",
    samples_count: "{count} chữ cái / {samples} mẫu",
    loading_runtime: "Đang nạp môi trường tính toán...",
    loading_package: "Đang nạp lõi Chữ Viết Tay...",
    loading_wheels: "Đang chuẩn bị thư viện toán & định dạng...",
    error_occurred: "Có lỗi xảy ra: {error}",
    guide_title: "Hướng dẫn sử dụng & Lưu ý khi vẽ",
    guide_btn_understood: "Đã hiểu",
    guide_help_btn: "Trợ giúp",
    btn_select_all: "Chọn tất cả",
    btn_deselect_all: "Bỏ chọn",
    btn_delete_selected: "Xoá đã chọn ({count})",
    confirm_batch_delete: "Bạn có chắc muốn xoá {count} ký tự đã chọn (tổng cộng {samples} mẫu nét) khỏi kho mẫu? Thao tác này không thể hoàn tác.",
    theme_light: "Giao diện sáng",
    theme_dark: "Giao diện tối",
  },
  en: {
    app_title: "Your Handwriting",
    app_subtitle: "Transform text into your authentic natural handwriting",
    tab_write: "Write",
    tab_teach: "Teach",
    tab_bank: "Bank",
    status_ready: "Ready",
    status_loading: "Loading...",
    status_saving: "Saving...",
    status_saved: "Saved to browser",
    status_syncing: "Syncing tabs...",
    btn_save: "Save",
    btn_clear: "Clear",
    btn_undo: "Undo",
    btn_export: "Export .xopp",
    btn_backup: "Backup Bank (.json.gz)",
    btn_import_bank: "Import Bank",
    btn_create_empty: "Create New Bank",
    input_placeholder: "Type your text here...",
    samples_count: "{count} letters / {samples} samples",
    loading_runtime: "Loading runtime environment...",
    loading_package: "Loading handwriting core...",
    loading_wheels: "Preparing math & layout libraries...",
    error_occurred: "An error occurred: {error}",
    guide_title: "User Guide & Drawing Tips",
    guide_btn_understood: "Understood",
    guide_help_btn: "Help",
    btn_select_all: "Select all",
    btn_deselect_all: "Deselect",
    btn_delete_selected: "Delete selected ({count})",
    confirm_batch_delete: "Are you sure you want to delete {count} selected characters ({samples} stroke samples) from the bank? This action cannot be undone.",
    theme_light: "Light theme",
    theme_dark: "Dark theme",
  },
};

let currentLang = "vi";

export function setLanguage(lang) {
  if (DICTIONARY[lang]) {
    currentLang = lang;
  }
}

export function t(key, params = {}) {
  const dict = DICTIONARY[currentLang] || DICTIONARY.vi;
  let text = dict[key] || DICTIONARY.vi[key] || key;
  for (const [k, v] of Object.entries(params)) {
    text = text.replace(new RegExp(`\\{${k}\\}`, "g"), v);
  }
  return text;
}
