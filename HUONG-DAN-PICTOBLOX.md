# HUONG DAN PICTOBLOX - CONG TRUONG AN TOAN + CAMERA AI

## File tai xuong
- cong-truong-an-toan-pictoblox.sb3  (Day du: Camera AI + Arduino)
- smart-school-crossing-pictoblox.sb3  (Chi Arduino - Upload Mode)

## Cach mo trong PictoBlox (https://pictoblox.ai/)
1. Mo PictoBlox -> File -> Open from Computer
2. Chon file .sb3
3. Board -> Arduino Uno
4. Connect -> chon cong COM
5. **Stage Mode** (che do mac dinh) cho file cong-truong-an-toan
6. Bam **Upload Firmware** (lan dau) roi **Green Flag**

## Truoc khi chay - Train Camera AI
1. Vao https://teachablemachine.withgoogle.com/
2. Tao project Image - Standard image model
3. Class 1: "Hoc sinh" (chup anh HS o khu cho)
4. Class 2: "Khong" (anh trong)
5. Train -> Export -> Link model
6. Trong PictoBlox sprite **Camera AI**, sua khoi "use model" -> dan URL model cua ban
7. Sua ten lop thanh "Hoc sinh" neu khac

## So do khoi - 2 Sprite

### Sprite 1: Camera AI
- Bat camera, nhan dien HS bang Teachable Machine
- Dat bien co_hs_ai = 1 khi phat hien "Hoc sinh"

### Sprite 2: Arduino Gate
- Dieu khien tat ca linh kien khi: co_hs_ai=1 AND cam bien IR AND sieu am > 30cm

## Chan noi Arduino
| Chan | Linh kien |
|------|-----------|
| 2,3,4 | Den GT xe |
| 5,6,7 | Den GT nguoi di |
| 8 | Buzzer |
| 9 | LED bao dong |
| 10 | Servo thanh chan |
| 11,12 | HC-SR04 |
| A0 | Cam bien hong ngoai |
| A4,A5 | LCD I2C |

## Quy trinh
1. Camera AI phat hien HS
2. IR + sieu am xac nhan
3. Arduino: den do xe, xanh nguoi, ha servo, bat coi+LED
4. Cho 5 giay -> tra ve binh thuong
