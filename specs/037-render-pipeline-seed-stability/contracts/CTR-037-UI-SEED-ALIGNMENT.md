# Contract CTR-037-UI-SEED-ALIGNMENT: Đồng bộ Giao diện và Báo cáo Hạt giống

## Mục đích
Quy định hiển thị hạt giống `seed_used` trên Desktop GUI, bổ sung điều khiển checkbox `stable_variants` trong Desktop GUI, và hiển thị thông báo lỗi trực quan `#opt-seed-error` trên Web Client.

---

## 1. Giao diện Desktop GUI (`chuviettay/view/write_tab.py`)

1. **Checkbox "Kiểu chữ ổn định"**:
   - Thêm biến điều khiển: `self.v_stable_variants = tk.BooleanVar(value=False)`
   - Đặt tại nhóm Tuỳ chỉnh nét chữ (`opt`):
     ```python
     ttk.Checkbutton(opt, text="Kiểu chữ ổn định khi chỉnh sửa (stable_variants)",
                     variable=self.v_stable_variants).pack(anchor="w", pady=(2, 0))
     ```
   - Trong `_build_options()`:
     ```python
     opts = WriteOptions(
         ...,
         stable_variants=self.v_stable_variants.get(),
         ...
     )
     ```

2. **Hiển thị `seed_used` trong Báo cáo Kết quả**:
   - Hàm `chuviettay/formatting.py:write_report_lines()` bổ sung:
     ```python
     if getattr(result, "seed_used", None) is not None:
         lines.append("Seed đã dùng: %d (chạy lại với --seed %d để có đúng kết quả này)" % (result.seed_used, result.seed_used))
     ```
   - Do cả Desktop GUI (`self.status`) và CLI đều gọi `write_report_lines(result)`, thông tin hạt giống được tự động hiển thị đầy đủ và đồng bộ.
   - Trong `chuviettay/cli.py:128-129`, xóa đoạn mã `print(f"Seed đã dùng: ...")` riêng lẻ để tránh in lặp 2 lần trên terminal.

---

## 2. Giao diện Web Client (`webapp/js/write.js` & `webapp/index.html`)

1. **Phần tử HTML cảnh báo**:
   - Trong `webapp/index.html`, dưới trường `<input id="opt-seed" ... />`, bổ sung:
     ```html
     <div id="opt-seed-error" class="error-msg" style="display:none; color: #dc3545; font-size: 0.8rem; margin-top: 4px;"></div>
     ```

2. **Xử lý sự kiện nhập Seed (Phòng thủ DOM)**:
   - Trong hàm `setupOptionsModal()` tại `write.js`:
     ```javascript
     const optSeed = document.getElementById("opt-seed");
     let optSeedError = document.getElementById("opt-seed-error");
     if (optSeed) {
       // Tạo fallback nếu phần tử chưa có trong DOM
       if (!optSeedError && optSeed.parentElement) {
         optSeedError = document.createElement("div");
         optSeedError.id = "opt-seed-error";
         optSeedError.className = "error-msg";
         optSeedError.style.cssText = "display:none; color: #dc3545; font-size: 0.8rem; margin-top: 4px;";
         optSeed.parentElement.appendChild(optSeedError);
       }

       optSeed.addEventListener("input", () => {
         if (optSeedError) optSeedError.style.display = "none";
         optSeed.classList.remove("is-invalid");
       });

       optSeed.addEventListener("change", (e) => {
         const parsed = parseSeed(e.target.value, writeOptions.seed);
         writeOptions.seed = parsed.seed;
         optSeed.value = parsed.seed !== null && parsed.seed !== undefined ? parsed.seed : "";
         if (!parsed.valid && parsed.message) {
           if (optSeedError) {
             optSeedError.textContent = parsed.message;
             optSeedError.style.display = "block";
           }
           optSeed.classList.add("is-invalid");
         } else {
           if (optSeedError) optSeedError.style.display = "none";
           optSeed.classList.remove("is-invalid");
         }
       });
     }
     ```
