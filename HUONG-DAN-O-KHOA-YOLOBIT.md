# Hướng dẫn: Ổ khóa Yolo:Bit (Bài tập 1)

## Tải chương trình

1. Mở [https://app.ohstem.vn/](https://app.ohstem.vn/)
2. Chọn **Lập trình Yolo:Bit**
3. Menu **Quản lý chương trình** → **Import project**
4. Chọn file **`o-khoa-yolo-bit.json`**
5. Vào **Mở rộng** → cài **AIOT Kit** và **MQTT** (nếu chưa có)
6. Sửa WiFi / username IoT trong khối lệnh hoặc tab MicroPython:
   - WiFi: `TenWiFi` / `MatKhauWiFi`
   - Username Bảng IoT: `SmartKey123`
7. Kết nối Yolo:Bit → **Chạy** → **Lưu project vào thiết bị**

### Tải file (chọn 1 cách)

**Cách 1 — Link trực tiếp (khuyên dùng):**

https://raw.githubusercontent.com/VuNam1208/Nhung/main/o-khoa-yolo-bit.json

- Mở link → trình duyệt hiện nội dung JSON
- Nhấn **Ctrl+S** (hoặc ⋮ → Lưu trang thành…)
- Đặt tên: `o-khoa-yolo-bit.json` (phải có đuôi `.json`)
- **Không** lưu thành `.html` hoặc `.txt`

**Cách 2 — GitHub:**

https://github.com/VuNam1208/Nhung/blob/main/o-khoa-yolo-bit.json

- Vào trang → nút **Raw** (góc phải) → Ctrl+S

**Cách 3 — Nếu vẫn lỗi:**

Mở OhStem → Import project → kéo thả file `o-khoa-yolo-bit.json` từ máy (nhờ bạn bè tải hộ qua link Cách 1 rồi gửi file).

## Kết nối phần cứng

| Thiết bị | Cổng |
|----------|------|
| LCD1602 (I2C) | I2C trên mạch mở rộng |
| Servo (khóa) | P6 |
| LED RGB (AIoT) | P0 |

## Chức năng chương trình

### Nhập mật khẩu (nút vật lý)

- **Nút A**: thêm ký tự `1`
- **Nút B**: thêm ký tự `2`
- **A + B**: kiểm tra mật khẩu
- Mật khẩu mặc định: `1221`
- Sai tối đa **3** lần → khóa nhập bằng nút, báo lên Bảng IoT

### Phản hồi khi kiểm tra

- **Đúng**: LCD *Mo khoa OK!*, nhạc POWER_UP, RGB xanh, Servo mở 2 giây
- **Sai**: LCD *Sai mat khau*, nhạc POWER_DOWN, RGB đỏ

## Tạo Bảng IoT (SMART KEY)

1. OhStem App → **Bảng điều khiển IoT** → Tạo bảng mới
2. Đặt **Username** (ví dụ `SmartKey123`) — phải trùng code
3. Kéo widget và gán **kênh MQTT**:

| Widget trên bảng | Kênh | Chức năng |
|------------------|------|-----------|
| Nút *Tạo MK mới* | `V3` | Bắt đầu nhập mật khẩu mới |
| Ô *Mật khẩu hiện tại* | `V1` | Hiển thị MK / MK đang nhập |
| Nút *1* | `V4` | Thêm ký tự 1 |
| Nút *2* | `V5` | Thêm ký tự 2 |
| Nút *Lưu* | `V6` | Lưu mật khẩu mới |
| (Tuỳ chọn) Nút mở khóa | `V2` | Mở khóa từ xa |
| (Tuỳ chọn) Nhãn cảnh báo | `V7` | Thông báo khi bị khóa |

4. Với mỗi **nút**, trong cài đặt widget chọn **Gửi giá trị** = `1` khi nhấn.

### Reset mật khẩu qua IoT (khi bị khóa)

1. Nhấn **Tạo MK mới** trên bảng
2. Nhấn **1** / **2** để ghép mật khẩu mới (tối thiểu 4 ký tự, ít nhất 2 ký tự khác nhau)
3. Xem trên ô **Mật khẩu hiện tại**
4. Nhấn **Lưu** → hệ thống mở khóa và dùng mật khẩu mới

## Kiểm thử nhanh

1. Nhập `1221` bằng A→1, B→2, A→1 rồi **A+B** → cửa mở
2. Nhập sai `3` lần → LCD *He thong khoa!*, không nhập thêm bằng nút
3. Trên Bảng IoT: Tạo MK mới → nhập `1212` → Lưu → thử mở bằng mật khẩu mới

## Lưu ý nộp bài

- Nộp file **`o-khoa-yolo-bit.json`** hoặc link chia sẻ project OhStem
- Chụp màn hình Bảng IoT + Yolo:Bit khi chạy thử
- Ghi rõ Username IoT và mật khẩu WiFi đã cấu hình
