# Dự án chấm công bằng Teachable Machine

File dự án: `cham-cong-teachable-machine.sb3`

## Cách mở

1. Mở <https://playground.raise.mit.edu/create/>.
2. Chọn **File → Load from your computer**.
3. Chọn file `cham-cong-teachable-machine.sb3`.
4. Trong khối `use model`, thay dòng hướng dẫn bằng URL mô hình Teachable Machine.
5. Bấm cờ xanh và cho phép trình duyệt sử dụng camera.

## Cách chấm công (lần lượt từng người)

1. Đợi 5 giây để mô hình tải xong.
2. Chương trình gọi **An** → An nhìn thẳng camera trong **15 giây**.
3. Nhận diện thành công → danh sách bên phải đổi `An: da den`.
4. Tiếp theo gọi **Binh**, rồi **Chi** theo cùng cách.
5. Cuối cùng thông báo đủ người hoặc ai vắng.

## Màn hình hiển thị

- Góc trái: `nguoi_dang_cho` (người đang được gọi), `person_time` (giây còn lại), `model prediction` (AI đang nhận diện gì).
- Góc phải: danh sách `danh_sach_cham_cong`.

## Cấu hình mặc định

- Mỗi người có 15 giây nhìn camera.
- Ba class của mô hình: `An`, `Binh`, `Chi`.

Tên class trên Teachable Machine phải giống chính xác `An`, `Binh`, `Chi`.

## Nếu vẫn không nhận diện

1. Kiểm tra `model prediction` có hiện đúng tên khi nhìn camera không.
2. Dán đúng link mô hình vào `use model`.
3. Huấn luyện lại với nhiều ảnh khuôn mặt hơn cho từng người.
4. Thêm class `Background` (ảnh không có người) trên Teachable Machine.
5. Mỗi người chỉ đứng trước camera khi được gọi tên ở `nguoi_dang_cho`.

Chạy `python3 create_attendance_sb3.py` để tạo lại file sau khi đổi cấu hình ở đầu script.
