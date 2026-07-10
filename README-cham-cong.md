# Dự án chấm công bằng Teachable Machine

File dự án: `cham-cong-teachable-machine.sb3`

## Cách mở

1. Mở <https://playground.raise.mit.edu/create/>.
2. Chọn **File → Load from your computer**.
3. Chọn file `cham-cong-teachable-machine.sb3`.
4. Trong khối `use model`, thay dòng hướng dẫn bằng URL mô hình Teachable Machine.
5. Bấm cờ xanh và cho phép trình duyệt sử dụng camera.

## Cấu hình mặc định

- Thời gian chấm công: 15 giây (nhìn vào camera trong 15 giây).
- Danh sách chấm công hiển thị ở góc phải màn hình (`danh_sach_cham_cong`).
- Ba class của mô hình: `An`, `Binh`, `Chi`.
- Chương trình chỉ ghi nhận mỗi thành viên một lần.
- Khi hết giờ, chương trình thông báo đầy đủ hoặc liệt kê người vắng.

Tên class trong Teachable Machine phải giống chính xác `An`, `Binh`, `Chi`. Có thể
đổi các tên này trong ba khối `when model detects` và phần thông báo nếu cần.

Chạy `python3 create_attendance_sb3.py` để tạo lại file dự án sau khi thay đổi cấu
hình ở đầu script.
