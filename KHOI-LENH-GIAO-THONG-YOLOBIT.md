# Khối lệnh — Giao thông thông minh Yolo:Bit

> Import file `giao-thong-thong-minh.json` để có sẵn khối, hoặc lắp theo hướng dẫn dưới.

## Biến (6 biến)

| Biến | Ý nghĩa |
|------|---------|
| `buoc den` | Bước chu trình 0–3 |
| `dem ket xe` | Đếm vòng lặp khi siêu âm gần |
| `dang ket xe` | 0/1 đã báo kẹt |
| `them xanh 1` | Cộng dồn thời gian xanh hướng 1 |
| `them xanh 2` | Cộng dồn thời gian xanh hướng 2 |
| `thong tin` | Dữ liệu MQTT nhận về |

## BẮT ĐẦU

```
đặt buoc den = 0
đặt dem ket xe = 0
đặt dang ket xe = 0
xóa màn hình Yolo:Bit
RGB P0 tắt (#000000)
Servo P6 → 20°
LCD: "Giao thong OK" / "San sang"
Khởi tạo siêu âm P10/P13
Kết nối WiFi + MQTT username "SmartTraffic123"
Gửi "BINH THUONG" → V1
[Đăng ký nhận V2..V6]
```

## LẶP LẠI MÃI

```
Kiểm tra tin nhắn MQTT
Nếu siêu âm < 15 cm:
    tăng dem ket xe
    nếu dem ket xe ≥ 50 và chưa báo:
        gửi "KET XE!" → V1
        LCD cảnh báo
Ngược lại: đặt dem ket xe = 0
Gửi khoảng cách → V7

Chu trình đèn (4 bước, sleep theo tham số):
  0: Xanh1-Đỏ2  → sleep 5000 ms
  1: Vàng1-Đỏ2  → sleep 2000 ms
  2: Đỏ1-Xanh2  → sleep 5000 ms
  3: Đỏ1-Vàng2  → sleep 2000 ms
```

## MQTT nhận lệnh

| Kênh | Khi nhận `1` |
|------|----------------|
| V2 | Tăng thời gian xanh hướng 1 |
| V3 | Tăng thời gian xanh hướng 2 |
| V4 | LCD đường vòng tránh |
| V5 | LCD mở làn chung |
| V6 | `1` bật đảo làn / `0` tắt |
