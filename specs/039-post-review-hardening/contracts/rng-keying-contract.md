# Contract: Deterministic ScopedRNG Keying and Independence

**Contract ID**: `CTR-039-RNG-KEYING`  
**Status**: Stable / Enforced  
**Applies to**: `chuviettay/layout/engine.py`, `chuviettay/model/rng.py`, `chuviettay/layout/math_layout.py`

---

## 1. Mục đích

Hợp đồng này quy định chặt chẽ cách thức cấu trúc khóa hạt giống cho bộ sinh số ngẫu nhiên cục bộ `ScopedRNG` khi `stable_variants=True`, đảm bảo tính tái lập 100%, tính độc lập giữa các đối tượng nội dung khác nhau, và tính bất biến khi chèn thêm tiền tố (Prepend Invariance).

---

## 2. Quy tắc Khóa Hình học Dòng (`_render_text_line`)

1. Khi duyệt qua các phần tử `item` trong `line_items`:
   - Trường `token_id` của `item` là nguồn định danh duy nhất được sử dụng để xây dựng RNG hình học.
   - Nếu `item` là đối tượng `RenderItem` có `token_id` khác rỗng, khóa RNG hình học PHẢI là:
     $$\text{key} = (\text{effective\_seed}, \text{"geom"}, \text{item.token\_id})$$
   - Tuyệt đối KHÔNG sử dụng tọa độ Y, tọa độ X tuyệt đối, hay chỉ số thứ tự dòng/phần tử `it_idx` làm thành phần của khóa.

2. Cấu trúc `token_id` theo loại đối tượng:
   - **Văn bản**: `f"text:{chunk}#{occ}"`
   - **Ký hiệu**: `f"sym:{symbol}#{occ}"`
   - **Ô bảng**: `f"cell:{row}_{col}:{chunk}#{occ}"`
   - **Công thức inline**: `f"math_tok:{chunk}#{occ}"`

---

## 3. Quy tắc Hạt giống Công thức Toán học

1. Mọi công thức toán học (`MathInline` hoặc `MathBlock`) khi `stable_variants=True` PHẢI nhận hạt giống riêng biệt dẫn xuất từ:
   - Đối với công thức Inline:
     $$\text{seed}_{\text{math}} = \text{ScopedRNG}(\text{effective\_seed}, \text{"math"}, \text{latex}, \text{occurrence}).\text{seed}$$
   - Đối với công thức Display Block:
     $$\text{seed}_{\text{math}} = \text{ScopedRNG}(\text{effective\_seed}, \text{"math\_block"}, \text{latex}, \text{occurrence}).\text{seed}$$

2. Bộ đếm `occurrence`:
   - Được duy trì ở cấp độ thực thể `DocumentLayoutEngine`.
   - Bắt đầu từ `0` cho lần đầu tiên xuất hiện của chuỗi `latex`.
   - Mỗi lần lặp lại của cùng chuỗi `latex` trong cùng một tài liệu làm tăng `occurrence` thêm `1`.

---

## 4. Cam kết Bất biến (Prepend Invariance Guarantees)

1. Khi chèn thêm văn bản hoặc công thức mới ở đoạn trước:
   - Các token ở đoạn sau không thay đổi `token_id` -> giữ nguyên 100% hình học nét vi mô.
   - Các công thức toán có nội dung LaTeX khác biệt với phần được chèn thêm không thay đổi `occurrence` -> giữ nguyên 100% hạt giống công thức.
