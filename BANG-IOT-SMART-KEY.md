# Bảng IoT SMART KEY — Hướng dẫn lập theo yêu cầu bài tập

> Bảng này dùng khi nhập sai mật khẩu quá nhiều lần → khóa nút vật lý → reset mật khẩu qua IoT.

## Thông tin chung

| Mục | Giá trị |
|-----|---------|
| Tên bảng | **SMART KEY** |
| Username | `SmartKey123` *(đổi tên riêng nếu bị trùng, nhưng phải sửa y hệt trong code Yolo:Bit)* |
| Server MQTT | `mqtt.ohstem.vn` (OhStem tự dùng) |

---

## Sơ đồ bố trí (giống minh họa đề bài)

```
              ┌─────────────────┐
              │   Tạo MK mới    │  ← Nút, kênh V3
              └─────────────────┘

┌──────┐   ┌───────────────────────┐   ┌──────┐
│  1   │   │   Mật khẩu hiện tại   │   │  2   │
│  V4  │   │        1221           │   │  V5  │
└──────┘   │      (kênh V1)        │   └──────┘
           └───────────────────────┘

              ┌─────────────────┐
              │       Lưu       │  ← Nút, kênh V6
              └─────────────────┘
```

---

## Bước 1 — Tạo bảng mới

1. Mở [https://app.ohstem.vn/](https://app.ohstem.vn/)
2. Chọn **Bảng điều khiển IoT**
3. Nhấn **Tạo mới**
4. Đặt tên bảng: **SMART KEY**
5. Đặt **Username**: `SmartKey123`  
   *(Thêm số nếu báo trùng, VD: `SmartKey123Nam` — rồi sửa username trong khối MQTT của Yolo:Bit)*

---

## Bước 2 — Kéo 5 widget ra màn hình

| STT | Loại widget (OhStem) | Tên hiển thị | Kênh | Ghi chú |
|-----|----------------------|--------------|------|---------|
| 1 | **Widget thông tin** / Label / Text | Mật khẩu hiện tại | **V1** | Chỉ hiển thị, Yolo:Bit gửi lên |
| 2 | **Nút bấm** (Button) | Tạo MK mới | **V3** | Gửi giá trị `1` khi nhấn |
| 3 | **Nút bấm** | 1 | **V4** | Gửi giá trị `1` khi nhấn |
| 4 | **Nút bấm** | 2 | **V5** | Gửi giá trị `1` khi nhấn |
| 5 | **Nút bấm** | Lưu | **V6** | Gửi giá trị `1` khi nhấn |

> **Không cần** V2, V7 cho đúng yêu cầu đề bài (chỉ 5 widget trên).

---

## Bước 3 — Cấu hình từng widget

### Widget 1: Mật khẩu hiện tại (V1)

1. Nhấn vào widget → **Cài đặt**
2. **Tên widget**: `Mật khẩu hiện tại`
3. **Kênh thông tin**: `V1`
4. **Kiểu hiển thị**: Text / Văn bản
5. Giá trị ban đầu có thể để trống hoặc `1221` (Yolo:Bit sẽ tự gửi khi chạy)

**Yolo:Bit gửi lên V1:**
- Lúc khởi động: mật khẩu đang cài (VD: `1221`)
- Khi đang tạo MK mới: chuỗi đang gõ (VD: `1`, `12`, `1212`)
- Khi bắt đầu reset: xóa ô (`""`)

---

### Widget 2: Tạo MK mới (V3) — nút Reset

1. Nhấn vào nút → **Cài đặt**
2. **Tên widget**: `Tạo MK mới`
3. **Kênh thông tin**: `V3`
4. **Giá trị gửi khi nhấn**: `1` *(bắt buộc)*

**Chức năng:** Bắt đầu nhập mật khẩu mới trên bảng IoT.

---

### Widget 3: Nút 1 (V4)

1. **Tên widget**: `1`
2. **Kênh thông tin**: `V4`
3. **Giá trị gửi khi nhấn**: `1`

**Chức năng:** Thêm ký tự `1` vào mật khẩu mới → hiện trên V1.

---

### Widget 4: Nút 2 (V5)

1. **Tên widget**: `2`
2. **Kênh thông tin**: `V5`
3. **Giá trị gửi khi nhấn**: `1`

**Chức năng:** Thêm ký tự `2` vào mật khẩu mới → hiện trên V1.

---

### Widget 5: Lưu (V6)

1. **Tên widget**: `Lưu`
2. **Kênh thông tin**: `V6`
3. **Giá trị gửi khi nhấn**: `1`

**Chức năng:** Lưu mật khẩu mới (tối thiểu 4 ký tự, có ít nhất 2 ký tự khác nhau).

---

## Bước 4 — Sắp xếp giao diện

Kéo widget theo bố cục đề bài:

1. **Trên cùng, giữa**: Tạo MK mới  
2. **Giữa**: Mật khẩu hiện tại (ô lớn nhất)  
3. **Trái** ô hiển thị: nút `1`  
4. **Phải** ô hiển thị: nút `2`  
5. **Dưới cùng, giữa**: Lưu  

Chọn nền / màu tuỳ ý (đề bài minh hoạ nền xanh đậm).

---

## Bước 5 — Liên kết với Yolo:Bit

Trong chương trình ổ khóa (`o-khoa-yolo-bit.json`):

| Khối lệnh | Giá trị phải trùng bảng IoT |
|-----------|------------------------------|
| kết nối server OhStem username | `SmartKey123` |
| gửi … đến chủ đề | `V1` |
| khi nhận … chủ đề `V3` | Tạo MK mới |
| khi nhận … chủ đề `V4` | Nút 1 |
| khi nhận … chủ đề `V5` | Nút 2 |
| khi nhận … chủ đề `V6` | Lưu |

---

## Bước 6 — Kiểm thử bảng IoT

### Chuẩn bị
1. Yolo:Bit đã kết nối WiFi + MQTT thành công
2. Bảng IoT ở chế độ **Play / Điều khiển** (không phải chế độ sửa)

### Test 1 — Hiển thị mật khẩu
- Chạy Yolo:Bit → ô **Mật khẩu hiện tại** hiện `1221`

### Test 2 — Reset mật khẩu (khi bị khóa)
1. Nhập sai mật khẩu **3 lần** trên Yolo:Bit → hệ thống khóa
2. Trên bảng IoT:
   - Nhấn **Tạo MK mới** → ô V1 xóa, LCD Yolo:Bit: *Nhap MK moi*
   - Nhấn **1** → **2** → **1** → **2** → V1 hiện `1212`
   - Nhấn **Lưu** → V1 hiện `1212`, hệ thống mở khóa
3. Trên Yolo:Bit: gõ `1212` bằng nút A/B → mở khóa được

---

## Bảng tra nhanh kênh ↔ yêu cầu đề bài

| Yêu cầu đề bài | Widget | Kênh |
|----------------|--------|------|
| Nút Reset (tạo mật khẩu mới) | Tạo MK mới | **V3** |
| Nút Lưu mật khẩu mới | Lưu | **V6** |
| Nút ký tự thứ nhất | 1 | **V4** |
| Nút ký tự thứ hai | 2 | **V5** |
| Hiển thị mật khẩu sau reset | Mật khẩu hiện tại | **V1** |

---

## Lỗi thường gặp

| Triệu chứng | Cách sửa |
|-------------|----------|
| Nhấn nút không phản hồi | Kiểm tra giá trị gửi = `1`; Yolo:Bit đã kết nối WiFi/MQTT |
| V1 không đổi | Username bảng IoT ≠ username trong code |
| Lưu không được | MK < 4 ký tự hoặc chỉ 1 loại ký tự (VD: `1111`) |
| Bảng không cập nhật | Chuyển bảng sang chế độ **Play** |

---

## Nộp bài

Chụp màn hình:
1. Bảng IoT SMART KEY (đủ 5 widget, đúng kênh)
2. Yolo:Bit đang chạy + LCD hiển thị
3. (Tuỳ chọn) Quá trình reset MK qua bảng
