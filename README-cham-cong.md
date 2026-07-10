# Dự án chấm công bằng Teachable Machine

File dự án: `cham-cong-teachable-machine.sb3`

## Quan trọng: tên class phải khớp

Trên Teachable Machine, tên 3 class phải **giống hệt** trong chương trình:

- `Trang`
- `Binh`
- `Chi`

Khi nhìn camera, ô `model prediction` phải hiện đúng tên người đang được gọi ở `nguoi_dang_cho`.

Ví dụ: nếu `model prediction` = `Trang` nhưng chương trình gọi `An` → sẽ **luôn báo vắng**.

Đổi tên trong file `create_attendance_sb3.py` dòng `MEMBERS = (...)` nếu bạn dùng tên khác, rồi chạy `python3 create_attendance_sb3.py`.

## Cách mở

1. Mở <https://playground.raise.mit.edu/create/>.
2. **File → Load from your computer** → chọn `cham-cong-teachable-machine.sb3`.
3. Dán link Teachable Machine vào khối `use model`.
4. Bấm cờ xanh, cho phép camera.

## Cách chấm công

1. Đợi 5 giây tải model.
2. Lượt **Trang** → nhìn camera 15 giây.
3. Lượt **Binh** → nhìn camera 15 giây.
4. Lượt **Chi** → nhìn camera 15 giây.
5. Kết quả: đủ người hoặc báo vắng.

## Màn hình

- `nguoi_dang_cho`: ai đang được gọi
- `person_time`: giây còn lại
- `model prediction`: AI đang nhận ra ai
- `danh_sach_cham_cong`: danh sách bên phải

## Kiểm tra nhanh

| `nguoi_dang_cho` | `model prediction` | Kết quả |
|---|---|---|
| Trang | Trang | Chấm công thành công |
| Trang | Background | Chưa nhận — nhìn rõ hơn / huấn luyện lại |
| Trang | Binh | Sai người — đợi đúng lượt |
