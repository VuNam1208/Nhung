# Dự án chấm công - giống bài mẫu Thu Trang

File: `cham-cong-teachable-machine.sb3`

## Giống bài mẫu của bạn

- 3 class Teachable Machine: **Trang**, **Thỏ**, **rắn**
- Danh sách: **Danh sách chấm công**
- Phím **`a`** để bắt đầu chấm công
- Broadcast **Thời gian chấm công** / **Hết giờ**
- Nhận diện bằng khối **`prediction is`**
- Báo vắng: Thu Trang, Thỏ, rắn

## Cách dùng

1. Mở <https://playground.raise.mit.edu/create/>
2. **File → Load from your computer** → chọn file `.sb3`
3. Dán link Teachable Machine vào khối `use model`
4. Bấm **cờ xanh** (tải model)
5. Bấm phím **`a`** để chấm công
6. Lần lượt từng người nhìn camera trong 10 giây
7. Khi hết giờ → báo đủ người hoặc vắng

## Khác bài mẫu (đã sửa cho chạy ổn hơn)

Bài mẫu chỉ kiểm tra `prediction is` **một lần** sau phím `a` nên dễ bỏ sót.

File này thêm **vòng lặp liên tục** trong lúc đếm ngược để nhận diện đúng khi nhìn camera.

## Sprites

- **Avery**: logic chấm công
- **Bang dem**: đếm ngược `time` và phát **Hết giờ**
