# Hướng dẫn: Giao thông thông minh Yolo:Bit (Bài tập 2)

## Tải chương trình

**Quan trọng — làm đúng thứ tự:**

1. Mở [https://app.ohstem.vn/](https://app.ohstem.vn/) → **Lập trình Yolo:Bit**
2. **Mở rộng** → cài **AIOT Kit** + **MQTT** trước (chờ báo cài xong)
3. **Quản lý chương trình** → **Import project** → file JSON bên dưới
4. Nếu màn hình trống: **Ctrl+F5** tải lại trang → Import lại
5. Sửa WiFi / username IoT:
   - WiFi: `Haha` / `0383075064`
   - Username Bảng IoT: `SmartTraffic123`
6. **Chạy** → **Lưu project vào thiết bị**

Tải trực tiếp từ GitHub (nhánh `main`):

`https://raw.githubusercontent.com/VuNam1208/Nhung/main/giao-thong-thong-minh.json`

## Kết nối phần cứng

| Thiết bị | Cổng |
|----------|------|
| Cảm biến siêu âm (trigger/echo) | **P10 / P13** |
| LED RGB hướng 2 | **P0** |
| Servo (dải phân cách / thanh chắn) | **P6** |
| LCD1602 (I2C) | I2C trên mạch mở rộng |
| Đèn hướng 1 | **LED 5×5 tích hợp Yolo:Bit** |

## Tham số tự chọn (ghi trong bài nộp)

| Tham số | Giá trị mặc định | Ý nghĩa |
|---------|------------------|---------|
| Thời gian đèn xanh | `5000` ms | Mỗi lượt xanh |
| Thời gian đèn vàng | `2000` ms | Mỗi lượt vàng |
| Ngưỡng kẹt xe | `15` cm | Siêu âm nhỏ hơn = có xe |
| Thời gian xác nhận kẹt | `5000` ms | Giữ ngưỡng bao lâu |
| Servo bình thường | `20`° | Làn mặc định |
| Servo đảo chiều | `110`° | Mở thêm làn |

## Chế độ bình thường

Hai bộ đèn chạy chu trình:

1. **Xanh 1 – Đỏ 2**
2. **Vàng 1 – Đỏ 2**
3. **Đỏ 1 – Xanh 2**
4. **Đỏ 1 – Vàng 2** → lặp lại

- Hướng 1: ma trận LED trên Yolo:Bit
- Hướng 2: LED RGB ngoài (P0)

## Chế độ kẹt xe & IoT

- Siêu âm < `15` cm liên tục `5000` ms → gửi **`KET XE!`** lên kênh `V1`
- Bảng IoT điều khiển:
  - `V2`: kéo dài xanh hướng 1
  - `V3`: kéo dài xanh hướng 2
  - `V4`: LCD hướng đi vòng tránh
  - `V5`: LCD cho phép dùng làn chung
  - `V6`: kích hoạt servo đảo làn (`1` = bật, `0` = tắt)
  - `V7`: khoảng cách siêu âm (cm)

Chi tiết bảng IoT: xem **`BANG-IOT-GIAO-THONG.md`**

## Kiểm thử nhanh

1. Chạy chương trình → hai bộ đèn chuyển màu đúng chu trình
2. Đưa tay/tấm bìa gần siêu âm > 5 giây → Bảng IoT báo **KET XE!**
3. Nhấn nút trên IoT → LCD / servo / thời gian xanh thay đổi

## Nộp bài

- File **`giao-thong-thong-minh.json`**
- Ảnh chụp Bảng IoT + Yolo:Bit khi chạy
- Ghi rõ username IoT và các tham số đã chọn
