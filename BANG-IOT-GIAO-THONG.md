# Bảng IoT — Giao thông thông minh (Bài tập 2)

## Thông tin chung

| Mục | Giá trị |
|-----|---------|
| Tên bảng | **SMART TRAFFIC** |
| Username | `TenUsernameIoT` |
| Server | `mqtt.ohstem.vn` |

## Widget đề xuất

| Widget | Tên hiển thị | Kênh | Chức năng |
|--------|--------------|------|-----------|
| Label | Trạng thái / cảnh báo | **V1** | Hiện `BINH THUONG` hoặc `KET XE!` |
| Label | Khoảng cách (cm) | **V7** | Yolo:Bit gửi liên tục |
| Nút | Xanh lâu H1 | **V2** | Gửi `1` → thêm xanh hướng 1 |
| Nút | Xanh lâu H2 | **V3** | Gửi `1` → thêm xanh hướng 2 |
| Nút | Hướng vòng tránh | **V4** | Gửi `1` → LCD đường tránh |
| Nút | Mở làn chung | **V5** | Gửi `1` → LCD xe máy được đi |
| Nút | Đảo làn BẬT | **V6** | Gửi `1` → servo góc 90° |
| Nút | Đảo làn TẮT | **V6** | Gửi `0` → servo góc 0° |

## Cấu hình nút

Mỗi **nút bấm**: **Giá trị gửi khi nhấn** = `1` (riêng nút TẮT đảo làn = `0`).

## Liên kết code

Username trong khối **kết nối server OhStem** phải trùng **`TenUsernameIoT`**.

## Kiểm thử

1. Yolo:Bit kết nối WiFi + MQTT thành công
2. Bảng ở chế độ **Play**
3. Gây kẹt xe (che siêu âm) → `V1` = `KET XE!`
4. Nhấn các nút → LCD / servo / đèn phản hồi
