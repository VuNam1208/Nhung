# Lập trình Ổ khóa Yolo:Bit — theo khối lệnh OhStem App

> Cách đọc: kéo khối từ danh mục bên trái vào **bắt đầu / lặp lại mãi** theo đúng thứ tự dưới đây.
> Hoặc **Import** file `o-khoa-yolo-bit.json` để có sẵn toàn bộ khối.

---

## Bước 0 — Tạo biến (mục **Biến**)

Tạo 7 biến:

| Tên biến | Ý nghĩa |
|----------|---------|
| `mat khau cai dat` | Mật khẩu đúng |
| `mat khau nhap` | Mật khẩu đang gõ |
| `dem sai` | Đếm số lần nhập sai |
| `khoa vat ly` | 0 = bình thường, 1 = đã khóa nút |
| `dang reset mk` | 0/1 — đang tạo MK mới qua IoT |
| `mk moi` | Mật khẩu mới đang nhập trên IoT |
| `thong tin` | Dữ liệu nhận từ Bảng IoT |

---

## Bước 1 — Khối gốc (mục **CƠ BẢN**)

```
bắt đầu
└── lặp lại mãi
    ├── [phần BẮT ĐẦU — ONSTART]
    └── [phần LẶP LẠI — FOREVER]
```

---

## Bước 2 — Phần BẮT ĐẦU (trong `bắt đầu`)

### 2.1 Khởi tạo biến (mục **Biến**)

```
đặt mat khau cai dat thành "1221"
đặt mat khau nhap thành ""
đặt dem sai thành 0
đặt khoa vat ly thành 0
đặt dang reset mk thành 0
đặt mk moi thành ""
```

### 2.2 Màn hình & đèn (mục **AIOT KIT**)

```
xóa màn hình LCD
hiển thị "Nhap MK" tại x 0 y 0
tất cả LED RGB chân P0 đổi màu led 0 thành #000000
```

### 2.3 Kết nối IoT (mục **MQTT**)

```
kết nối WiFi "TenWiFi" mật khẩu "MatKhauWiFi"
kết nối đến server OhStem với username "SmartKey123" key ""
gửi mat khau cai dat đến chủ đề "V1"
```

*(Sửa `TenWiFi`, `MatKhauWiFi`, `SmartKey123` cho đúng thiết bị của bạn.)*

---

## Bước 3 — Nhận lệnh từ Bảng IoT (mục **MQTT**, trong BẮT ĐẦU)

### 3.1 Kênh V2 — Mở khóa từ xa

```
khi nhận được thong tin gửi vào chủ đề "V2"
    nếu khoa vat ly ≠ 1  và  thong tin = "1" thì
        [gọi khối MỞ KHOA — xem mục 5]
```

### 3.2 Kênh V3 — Tạo mật khẩu mới

```
khi nhận được thong tin gửi vào chủ đề "V3"
    nếu thong tin = "1" thì
        đặt dang reset mk thành 1
        đặt mk moi thành ""
        gửi "" đến chủ đề "V1"
        xóa màn hình LCD
        hiển thị "Nhap MK moi" tại x 0 y 0
```

### 3.3 Kênh V4 — Nút 1 trên Bảng IoT

```
khi nhận được thong tin gửi vào chủ đề "V4"
    nếu dang reset mk = 1 thì
        đặt mk moi thành nối (mk moi, "1")
        gửi mk moi đến chủ đề "V1"
```

### 3.4 Kênh V5 — Nút 2 trên Bảng IoT

```
khi nhận được thong tin gửi vào chủ đề "V5"
    nếu dang reset mk = 1 thì
        đặt mk moi thành nối (mk moi, "2")
        gửi mk moi đến chủ đề "V1"
```

### 3.5 Kênh V6 — Lưu mật khẩu mới

```
khi nhận được thong tin gửi vào chủ đề "V6"
    nếu dang reset mk = 1  và  thong tin = "1" thì
        đặt mat khau cai dat thành mk moi
        đặt mk moi thành ""
        đặt dang reset mk thành 0
        đặt dem sai thành 0
        đặt khoa vat ly thành 0
        gửi mat khau cai dat đến chủ đề "V1"
        xóa màn hình LCD
        hiển thị "Luu MK OK" tại x 0 y 0
        tất cả LED RGB chân P0 đổi màu #00ff00
        phát nhạc POWER_UP
```

---

## Bước 4 — Phần LẶP LẠI MÃI (trong `lặp lại mãi`)

```
cập nhật thông tin từ server

nếu khoa vat ly ≠ 1 thì
    nếu nút A+B được nhấn thì
        [KIỂM TRA MẬT KHẨU — mục 6]
    nếu không
        nếu nút A được nhấn thì
            phát nốt nhạc G3
            đặt mat khau nhap thành nối (mat khau nhap, "1")
            xóa màn hình LCD
            hiển thị mat khau nhap tại x 0 y 0
            tạm dừng 250 ms
        nếu không
            nếu nút B được nhấn thì
                phát nốt nhạc G3
                đặt mat khau nhap thành nối (mat khau nhap, "2")
                xóa màn hình LCD
                hiển thị mat khau nhap tại x 0 y 0
                tạm dừng 250 ms

tạm dừng 80 ms
```

---

## Bước 5 — Khối con: MỞ KHOA (dùng lại nhiều chỗ)

```
xóa màn hình LCD
hiển thị "Mo khoa OK!" tại x 0 y 0
tất cả LED RGB chân P0 đổi màu #00ff00
phát nhạc POWER_UP
quay servo chân P6 đến góc 90
tạm dừng 2000 ms
quay servo chân P6 đến góc 0
tắt điều khiển servo chân P6
đặt dem sai thành 0
đặt mat khau nhap thành ""
tất cả LED RGB chân P0 đổi màu #000000
```

---

## Bước 6 — Khối con: KIỂM TRA MẬT KHẨU (khi nhấn A+B)

```
nếu mat khau nhap = mat khau cai dat thì
    [MỞ KHOA — mục 5]
nếu không thì
    đặt dem sai thành dem sai + 1
    xóa màn hình LCD
    hiển thị "Sai mat khau" tại x 0 y 0
    tất cả LED RGB chân P0 đổi màu #ff0000
    phát nhạc POWER_DOWN
    đặt mat khau nhap thành ""
    nếu dem sai ≥ 3 thì
        đặt khoa vat ly thành 1
        xóa màn hình LCD
        hiển thị "He thong khoa!" tại x 0 y 0
        gửi "KHOA: Sai qua nhieu lan" đến chủ đề "V7"
        gửi mat khau cai dat đến chủ đề "V1"
```

---

## Bước 7 — Bảng IoT (SMART KEY)

| Widget | Kênh | Giá trị gửi |
|--------|------|-------------|
| Tạo MK mới | V3 | 1 |
| Mật khẩu hiện tại | V1 | (nhận từ Yolo:Bit) |
| Nút 1 | V4 | 1 |
| Nút 2 | V5 | 1 |
| Lưu | V6 | 1 |
| Mở khóa (tuỳ chọn) | V2 | 1 |
| Cảnh báo (tuỳ chọn) | V7 | (nhận từ Yolo:Bit) |

---

## Thử nhanh

| Thao tác | Kết quả |
|----------|---------|
| A → B → A → **A+B** | Mở khóa (MK `1221`) |
| Nhập sai 3 lần | LCD *He thong khoa!*, không gõ nút nữa |
| IoT: Tạo MK → 1 → 2 → 1 → 2 → Lưu | MK mới = `1212` |

---

## Import nhanh (không cần kéo từng khối)

1. OhStem → **Import project** → chọn `o-khoa-yolo-bit.json`
2. Sửa WiFi / username → **Chạy** → **Lưu vào thiết bị**

Tải file: https://github.com/VuNam1208/Nhung/raw/cursor/yolobit-smart-lock-6e7f/o-khoa-yolo-bit.json
