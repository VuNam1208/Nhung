#!/usr/bin/env python3
"""Generate OhStem Yolo:Bit project: Smart traffic (Bài tập 2)."""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT = Path(__file__).with_name("giao-thong-thong-minh.json")
OUTPUT_TEST = Path(__file__).with_name("test-sieu-am.json")
GUIDE = Path(__file__).with_name("HUONG-DAN-GIAO-THONG-YOLOBIT.md")
BLOCK_GUIDE = Path(__file__).with_name("KHOI-LENH-GIAO-THONG-YOLOBIT.md")
IOT_GUIDE = Path(__file__).with_name("BANG-IOT-GIAO-THONG.md")

# --- Sửa 3 dòng này trên OhStem App sau khi import (không ghi sẵn WiFi/username) ---
WIFI_NAME = "TenWiFi"
WIFI_PASS = "MatKhauWiFi"
IOT_USERNAME = "TenUsernameIoT"

# Phase timing (milliseconds) — tham số tự chọn (ghi rõ trong bài)
GREEN_MS = 5000
YELLOW_MS = 2000

# Ultrasonic jam detection — P10/P13
JAM_DISTANCE_CM = 15
JAM_HOLD_MS = 5000
LOOP_MS = 100

# Servo lane barrier — P6 (0° / 90° giống khóa thông minh OhStem)
SERVO_NORMAL = 0
SERVO_REVERSE = 90

# Extra green time from IoT (milliseconds per button press)
IOT_GREEN_BONUS_MS = 3000

EXTENSIONS = [
    {
        "id": "yolobit-AITT-VN-yolobit_extension_aiot",
        "src": "https://github.com/AITT-VN/yolobit_extension_aiot",
        "name": "AIOT Kit",
        "description": "Mục mở rộng dành cho bộ kit AIoT",
    },
    {
        "id": "yolobit-AITT-VN-yolobit_extension_mqtt",
        "src": "https://github.com/AITT-VN/yolobit_extension_mqtt",
        "name": "MQTT",
        "description": "Kết nối Bảng điều khiển IoT qua MQTT",
    },
]

# MQTT channels
CH_STATUS = "V1"
CH_GREEN1 = "V2"
CH_GREEN2 = "V3"
CH_LCD_ROUTE = "V4"
CH_LCD_LANE = "V5"
CH_LANE_REV = "V6"
CH_DISTANCE = "V7"

# Matrix colours — direction 1 (Yolo:Bit 5×5)
MATRIX_GREEN = "#00ff00"
MATRIX_YELLOW = "#ffff00"
MATRIX_RED = "#ff0000"


class Xml:
    """Minimal Blockly XML builder for OhStem export."""

    def __init__(self) -> None:
        self._n = 0

    def bid(self) -> str:
        self._n += 1
        return f"b{self._n}"

    def field_var(self, var_id: str, name: str) -> str:
        return f'<field name="VAR" id="{var_id}">{name}</field>'

    def text(self, value: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        esc = value.replace("&", "&amp;").replace("<", "&lt;")
        return f'<block type="text" id="{bid}"><field name="TEXT">{esc}</field></block>'

    def num(self, value: int | str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="math_number" id="{bid}">'
            f'<field name="NUM">{value}</field></block>'
        )

    def var_get(self, var_id: str, name: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="variables_get" id="{bid}">'
            f"{self.field_var(var_id, name)}</block>"
        )

    def var_set(self, var_id: str, name: str, value_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="variables_set" id="{bid}">'
            f"{self.field_var(var_id, name)}"
            f'<value name="VALUE">{value_xml}</value></block>'
        )

    def compare_eq(self, a_xml: str, b_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="logic_compare" id="{bid}"><field name="OP">EQ</field>'
            f'<value name="A">{a_xml}</value><value name="B">{b_xml}</value></block>'
        )

    def compare_gte(self, a_xml: str, b_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="logic_compare" id="{bid}"><field name="OP">GTE</field>'
            f'<value name="A">{a_xml}</value><value name="B">{b_xml}</value></block>'
        )

    def logic_and(self, a_xml: str, b_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="logic_operation" id="{bid}"><field name="OP">AND</field>'
            f'<value name="A">{a_xml}</value><value name="B">{b_xml}</value></block>'
        )

    def logic_not(self, a_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return f'<block type="logic_negate" id="{bid}"><value name="BOOL">{a_xml}</value></block>'

    def chain(self, *blocks: str) -> str:
        if not blocks:
            return ""
        if len(blocks) == 1:
            return blocks[0]
        out = blocks[0]
        for nxt in blocks[1:]:
            close_idx = self._chain_tail_close_index(out)
            out = out[:close_idx] + f"<next>{nxt}</next>" + out[close_idx:]
        return out

    @staticmethod
    def _top_level_close_index(xml: str) -> int:
        depth = 0
        i = 0
        while i < len(xml):
            if xml.startswith("<block", i):
                depth += 1
                i += 6
                continue
            if xml.startswith("</block>", i):
                depth -= 1
                if depth == 0:
                    return i
                i += 8
                continue
            i += 1
        return xml.rfind("</block>")

    @staticmethod
    def _chain_tail_close_index(xml: str) -> int:
        close_idx = Xml._top_level_close_index(xml)
        inner = xml[:close_idx]
        depth = 0
        last_top_next = -1
        i = 0
        while i < len(inner):
            if inner.startswith("<block", i):
                depth += 1
                i += 6
                continue
            if inner.startswith("</block>", i):
                depth -= 1
                i += 8
                continue
            if depth == 1 and inner.startswith("<next>", i):
                last_top_next = i
                i += 6
                continue
            i += 1
        if last_top_next == -1:
            return close_idx
        after_next = inner[last_top_next + 6 :].lstrip()
        if not after_next.startswith("<block"):
            return close_idx
        lead = len(inner[last_top_next + 6 :]) - len(after_next)
        sub_tail = Xml._chain_tail_close_index(after_next)
        return last_top_next + 6 + lead + sub_tail

    def stmt_if(self, cond: str, do: str, else_do: str | None = None, bid: str | None = None) -> str:
        bid = bid or self.bid()
        mut = '<mutation else="1"></mutation>' if else_do else ""
        else_part = f'<statement name="ELSE">{else_do}</statement>' if else_do else ""
        return (
            f'<block type="controls_if" id="{bid}">{mut}'
            f'<value name="IF0">{cond}</value>'
            f'<statement name="DO0">{do}</statement>{else_part}</block>'
        )

    def sleep_ms(self, ms: int | str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        duration = self.num(ms) if isinstance(ms, int) else ms
        return (
            f'<block type="yolobit_basic_sleep" id="{bid}">'
            f'<value name="duration">{duration}</value></block>'
        )

    def rgb2(self, colour: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        sh = self.bid()
        return (
            f'<block type="aiot_led_tiny_set_all" id="{bid}">'
            f'<field name="port">pin0</field><field name="option">0</field>'
            f'<value name="COLOR"><shadow type="colour_picker" id="{sh}">'
            f'<field name="COLOUR">{colour}</field></shadow></value></block>'
        )

    def den1_matrix(self, colour: str) -> str:
        """Direction 1: native OhStem matrix blocks (show_image + create_image)."""
        img_id = self.bid()
        fields = "".join(
            f'<field name="{y}{x}">{colour}</field>' for y in range(5) for x in range(5)
        )
        create = f'<block type="yolobit_basic_create_image" id="{img_id}">{fields}</block>'
        show_id = self.bid()
        return (
            f'<block type="yolobit_basic_show_image" id="{show_id}">'
            f'<value name="image">{create}</value></block>'
        )

    def den1_led(self, colour: str, bid: str | None = None) -> str:
        """Alias — use OhStem-native matrix blocks instead of yolobit_led_set_all."""
        return self.den1_matrix(colour)

    def display_clear(self) -> str:
        return f'<block type="yolobit_basic_clear_display" id="{self.bid()}"></block>'

    def num_to_text(self, num_xml: str) -> str:
        join_id = self.bid()
        return (
            f'<block type="text_join" id="{join_id}"><mutation items="2"></mutation>'
            f'<value name="ADD0">{self.text("")}</value>'
            f'<value name="ADD1">{num_xml}</value></block>'
        )

    def lcd_line(self, text_xml: str, y: int) -> str:
        clear_id = self.bid()
        disp_id = self.bid()
        clear = f'<block type="aiot_lcd1602_clear" id="{clear_id}"></block>' if y == 0 else ""
        disp = (
            f'<block type="aiot_lcd1602_display" id="{disp_id}">'
            f'<value name="string">{text_xml}</value>'
            f'<value name="X">{self.num(0)}</value>'
            f'<value name="Y">{self.num(y)}</value></block>'
        )
        return self.chain(clear, disp) if clear else disp

    def lcd_two_lines(self, line1: str, line2: str) -> str:
        return self.chain(
            f'<block type="aiot_lcd1602_clear" id="{self.bid()}"></block>',
            (
                f'<block type="aiot_lcd1602_display" id="{self.bid()}">'
                f'<value name="string">{self.text(line1)}</value>'
                f'<value name="X">{self.num(0)}</value>'
                f'<value name="Y">{self.num(0)}</value></block>'
            ),
            (
                f'<block type="aiot_lcd1602_display" id="{self.bid()}">'
                f'<value name="string">{self.text(line2)}</value>'
                f'<value name="X">{self.num(0)}</value>'
                f'<value name="Y">{self.num(1)}</value></block>'
            ),
        )

    def lcd_line2_distance(self, var_id: str, name: str) -> str:
        join_id = self.bid()
        disp_id = self.bid()
        join = (
            f'<block type="text_join" id="{join_id}"><mutation items="3"></mutation>'
            f'<value name="ADD0">{self.text("KC: ")}</value>'
            f'<value name="ADD1">{self.num_to_text(self.var_get(var_id, name))}</value>'
            f'<value name="ADD2">{self.text(" cm")}</value></block>'
        )
        return (
            f'<block type="aiot_lcd1602_display" id="{disp_id}">'
            f'<value name="string">{join}</value>'
            f'<value name="X">{self.num(0)}</value>'
            f'<value name="Y">{self.num(1)}</value></block>'
        )

    def math_add(self, a_xml: str, b_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="math_arithmetic" id="{bid}"><field name="OP">ADD</field>'
            f'<value name="A">{a_xml}</value><value name="B">{b_xml}</value></block>'
        )

    def math_divide(self, a_xml: str, b_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="math_arithmetic" id="{bid}"><field name="OP">DIVIDE</field>'
            f'<value name="A">{a_xml}</value><value name="B">{b_xml}</value></block>'
        )

    def repeat_times(self, times_xml: str, body: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="controls_repeat_ext" id="{bid}">'
            f'<value name="TIMES">{times_xml}</value>'
            f'<statement name="DO">{body}</statement></block>'
        )

    def increment_var(self, var_id: str, name: str) -> str:
        return self.var_set(
            var_id,
            name,
            self.math_add(self.var_get(var_id, name), self.num(1)),
        )

    def add_to_var(self, var_id: str, name: str, amount: int) -> str:
        return self.var_set(
            var_id,
            name,
            self.math_add(self.var_get(var_id, name), self.num(amount)),
        )

    def servo_angle(self, angle: int) -> str:
        b = self.bid()
        return (
            f'<block type="yolobit_pin_servo_write_angle" id="{b}"><field name="pin">6</field>'
            f'<value name="angle">{self.num(angle)}</value></block>'
        )

    def servo_release(self) -> str:
        return (
            f'<block type="yolobit_pin_servo_release" id="{self.bid()}">'
            f'<field name="pin">6</field></block>'
        )

    def servo_move(self, angle: int) -> str:
        return self.chain(
            self.servo_angle(angle),
            self.sleep_ms(400),
            self.servo_release(),
        )

    def wait_active_ms(
        self,
        duration: int | str,
        jam_tick: str,
        v_dist: str,
        dist_name: str,
        ch_distance: str,
    ) -> str:
        if isinstance(duration, int):
            times_xml = self.num(duration // LOOP_MS)
        else:
            times_xml = self.math_divide(duration, self.num(LOOP_MS))
        tick = self.chain(
            self.mqtt_check(),
            jam_tick,
            self.var_set(v_dist, dist_name, self.ultrasonic_read_cm()),
            self.mqtt_publish(ch_distance, self.var_get(v_dist, dist_name)),
            self.lcd_line2_distance(v_dist, dist_name),
            self.sleep_ms(LOOP_MS),
        )
        return self.repeat_times(times_xml, tick)

    def ultrasonic_create(self) -> str:
        b = self.bid()
        return (
            f'<block type="aiot_ultrasonic_create" id="{b}">'
            f'<field name="TRG">pin10</field><field name="ECH">pin13</field></block>'
        )

    def ultrasonic_near(self, cm: int) -> str:
        b = self.bid()
        return (
            f'<block type="aiot_ultrasonic_checkdistance" id="{b}">'
            f'<value name="DISTANCE">{self.num(cm)}</value>'
            f'<field name="TYPE">CM</field></block>'
        )

    def ultrasonic_read_cm(self) -> str:
        b = self.bid()
        return (
            f'<block type="aiot_ultrasonic_read" id="{b}"><field name="TYPE">CM</field></block>'
        )

    def mqtt_wifi(self) -> str:
        b = self.bid()
        return (
            f'<block type="yolobit_mqtt_connect_wifi" id="{b}">'
            f'<value name="WIFI">{self.text(WIFI_NAME)}</value>'
            f'<value name="PASSWORD">{self.text(WIFI_PASS)}</value></block>'
        )

    def mqtt_broker(self) -> str:
        b = self.bid()
        return (
            f'<block type="yolobit_mqtt_connect_default_servers" id="{b}">'
            f'<field name="SERVER">mqtt.ohstem.vn</field>'
            f'<value name="USERNAME">{self.text(IOT_USERNAME)}</value>'
            f'<value name="KEY">{self.text("")}</value></block>'
        )

    def mqtt_publish(self, topic: str, msg_xml: str) -> str:
        b = self.bid()
        return (
            f'<block type="yolobit_mqtt_publish" id="{b}">'
            f'<value name="MESSAGE">{msg_xml}</value>'
            f'<value name="TOPIC">{self.text(topic)}</value></block>'
        )

    def mqtt_on_receive(self, topic: str, var_id: str, var_name: str, action: str) -> str:
        b = self.bid()
        return (
            f'<block type="yolobit_mqtt_on_receive_message" id="{b}">'
            f'<field name="message" id="{var_id}">{var_name}</field>'
            f'<value name="TOPIC">{self.text(topic)}</value>'
            f'<statement name="ACTION">{action}</statement></block>'
        )

    def mqtt_check(self) -> str:
        return f'<block type="yolobit_mqtt_check_message" id="{self.bid()}"></block>'


def build_python() -> str:
    return f'''from yolobit import *
import time
from mqtt import *
from aiot_lcd1602 import LCD1602
from aiot_rgbled import RGBLed
from aiot_hcsr04 import HCSR04

WIFI_NAME = '{WIFI_NAME}'
WIFI_PASS = '{WIFI_PASS}'
IOT_USER = '{IOT_USERNAME}'
XANH_MS = {GREEN_MS}
VANG_MS = {YELLOW_MS}
NGUONG_CM = {JAM_DISTANCE_CM}
Giu_KET_MS = {JAM_HOLD_MS}
VONG_MS = {LOOP_MS}
THEM_XANH_MS = {IOT_GREEN_BONUS_MS}
SERVO_BT = {SERVO_NORMAL}
SERVO_DAO = {SERVO_REVERSE}

aiot_lcd1602 = LCD1602()
tiny_rgb = RGBLed(pin0.pin, 4)
aiot_ultrasonic = None

buoc_den = 0
dem_ket = 0
dang_ket = 0
them_xanh_1 = 0
them_xanh_2 = 0
con_lai = 0
khoang_cach = 999

def hien_lcd(d1, d2=''):
  aiot_lcd1602.clear()
  aiot_lcd1602.move_to(0, 0)
  aiot_lcd1602.putstr(str(d1)[:16])
  if d2:
    aiot_lcd1602.move_to(0, 1)
    aiot_lcd1602.putstr(str(d2)[:16])

def den_huong1(mau):
  if mau == 'X':
    display.set_all('#00ff00')
  elif mau == 'V':
    display.set_all('#ffff00')
  elif mau == 'D':
    display.set_all('#ff0000')
  else:
    display.clear()

def den_huong2(mau):
  if mau == 'X':
    tiny_rgb.show(0, hex_to_rgb('#00ff00'))
  elif mau == 'V':
    tiny_rgb.show(0, hex_to_rgb('#ffff00'))
  elif mau == 'D':
    tiny_rgb.show(0, hex_to_rgb('#ff0000'))
  else:
    tiny_rgb.show(0, hex_to_rgb('#000000'))

def dat_den_h1(h1, h2):
  den_huong1(h1)
  den_huong2(h2)

def doc_khoang_cach():
  global khoang_cach
  if aiot_ultrasonic is None:
    khoang_cach = 999
    return 999
  try:
    khoang_cach = int(aiot_ultrasonic.distance_cm())
  except OSError:
    khoang_cach = 999
  return khoang_cach

def hien_kc(d1):
  kc = doc_khoang_cach()
  hien_lcd(d1, 'KC:' + str(kc) + 'cm')

def servo_giu(goc):
  pin6.servo_write(goc)
  time.sleep_ms(600)

def khoi_tao_sieu_am():
  global aiot_ultrasonic
  time.sleep_ms(500)
  aiot_ultrasonic = HCSR04(trigger_pin=pin10.pin, echo_pin=pin13.pin)
  time.sleep_ms(500)
  for _ in range(5):
    doc_khoang_cach()
    time.sleep_ms(150)

def khoi_tao_servo():
  servo_giu(SERVO_BT)
  time.sleep_ms(800)
  servo_giu(SERVO_DAO)
  time.sleep_ms(800)
  servo_giu(SERVO_BT)

def gui_trang_thai(msg):
  mqtt.publish('{CH_STATUS}', str(msg))

def gui_khoang_cach():
  kc = doc_khoang_cach()
  mqtt.publish('{CH_DISTANCE}', str(kc))
  aiot_lcd1602.move_to(0, 1)
  aiot_lcd1602.putstr(('KC:' + str(kc) + 'cm')[:16])

def kiem_tra_ket_xe():
  global dem_ket, dang_ket
  if doc_khoang_cach() < NGUONG_CM:
    dem_ket += 1
  else:
    dem_ket = 0
  if dem_ket * VONG_MS >= Giu_KET_MS and not dang_ket:
    dang_ket = 1
    gui_trang_thai('KET XE!')
    hien_lcd('CANH BAO KET XE', 'Dung tren IoT')

def bat_dau_pha(tg, h1, h2, lcd1, lcd2):
  global con_lai
  dat_den_h1(h1, h2)
  hien_lcd(lcd1, lcd2)
  con_lai = tg

def chuyen_pha():
  global buoc_den, them_xanh_1, them_xanh_2
  if buoc_den == 0:
    tg = XANH_MS + them_xanh_1
    them_xanh_1 = 0
    bat_dau_pha(tg, 'X', 'D', 'Huong 1: XANH', 'Huong 2: DO')
    buoc_den = 1
  elif buoc_den == 1:
    bat_dau_pha(VANG_MS, 'V', 'D', 'Huong 1: VANG', 'Huong 2: DO')
    buoc_den = 2
  elif buoc_den == 2:
    tg = XANH_MS + them_xanh_2
    them_xanh_2 = 0
    bat_dau_pha(tg, 'D', 'X', 'Huong 1: DO', 'Huong 2: XANH')
    buoc_den = 3
  else:
    bat_dau_pha(VANG_MS, 'D', 'V', 'Huong 1: DO', 'Huong 2: VANG')
    buoc_den = 0

def on_v2(msg):
  global them_xanh_1
  if str(msg) in ('1', 'MO'):
    them_xanh_1 += THEM_XANH_MS

def on_v3(msg):
  global them_xanh_2
  if str(msg) in ('1', 'MO'):
    them_xanh_2 += THEM_XANH_MS

def on_v4(msg):
  if str(msg) in ('1', 'MO'):
    hien_kc('KET XE TRUOC')

def on_v5(msg):
  if str(msg) in ('1', 'MO'):
    hien_kc('MO LANE CHUNG')

def on_v6(msg):
  if str(msg) in ('1', 'MO', 'ON'):
    servo_giu(SERVO_DAO)
    hien_kc('Dao lan ON')
  elif str(msg) in ('0', 'OFF'):
    servo_giu(SERVO_BT)
    hien_kc('Dao lan OFF')

def khoi_tao_mqtt():
  mqtt.connect_wifi(WIFI_NAME, WIFI_PASS)
  mqtt.connect_broker(server='mqtt.ohstem.vn', port=1883, username=IOT_USER, password='')
  mqtt.on_receive_message('{CH_GREEN1}', on_v2)
  mqtt.on_receive_message('{CH_GREEN2}', on_v3)
  mqtt.on_receive_message('{CH_LCD_ROUTE}', on_v4)
  mqtt.on_receive_message('{CH_LCD_LANE}', on_v5)
  mqtt.on_receive_message('{CH_LANE_REV}', on_v6)
  gui_trang_thai('BINH THUONG')

display.clear()
tiny_rgb.show(0, hex_to_rgb('#000000'))
hien_lcd('Khoi tao...', 'Sieu am P10/13')
khoi_tao_sieu_am()
hien_lcd('Sieu am OK', str(doc_khoang_cach()) + ' cm')
time.sleep_ms(2500)
hien_lcd('Test servo...', 'P6')
khoi_tao_servo()
hien_lcd('Giao thong OK', 'Ket noi IoT')
khoi_tao_mqtt()
chuyen_pha()

while True:
  mqtt.check_message()
  kiem_tra_ket_xe()
  gui_khoang_cach()
  if button_a.is_pressed() and not button_b.is_pressed():
    servo_giu(SERVO_DAO)
    hien_kc('Nut A: Dao ON')
  if button_b.is_pressed() and not button_a.is_pressed():
    servo_giu(SERVO_BT)
    hien_kc('Nut B: Dao OFF')
  if con_lai <= 0:
    chuyen_pha()
  else:
    con_lai -= VONG_MS
  time.sleep_ms(VONG_MS)
'''


def build_xml() -> str:
    """Minimal Blockly stub — logic runs from embedded Python."""
    return (
        '<xml xmlns="https://developers.google.com/blockly/xml">'
        '<block type="yolobit_basic_forever" id="main" x="20" y="20">'
        '<statement name="ONSTART"></statement>'
        '<statement name="FOREVER"></statement>'
        "</block></xml>"
    )


def build_guide() -> str:
    return f"""# Hướng dẫn: Giao thông thông minh Yolo:Bit (Bài tập 2)

## Tải chương trình

**Quan trọng — làm đúng thứ tự:**

1. Mở [https://app.ohstem.vn/](https://app.ohstem.vn/) → **Lập trình Yolo:Bit**
2. **Mở rộng** → cài **AIOT Kit** + **MQTT** trước (chờ báo cài xong)
3. **Quản lý chương trình** → **Import project** → file JSON bên dưới
4. **Bật chế độ Python** (nút trên cùng giao diện) — code chạy từ Python, không phải khối lệnh
5. Sửa WiFi / username IoT:
   - WiFi: `{WIFI_NAME}` / `{WIFI_PASS}`
   - Username Bảng IoT: `{IOT_USERNAME}`
6. **Chạy** → **Lưu project vào thiết bị**

## Kiểm tra phần cứng khi bật nguồn

| Thứ tự | LCD hiện | Ý nghĩa |
|--------|----------|---------|
| 1 | `Khoi tao...` / `Sieu am P10/13` | Đang khởi tạo siêu âm |
| 2 | `Sieu am OK` + số cm | Cảm biến hoạt động |
| 3 | `Test servo...` / `P6` | Servo quay 0°→90°→0° |
| 4 | `Giao thong OK` | Kết nối IoT |
| 5 | Dòng 2: `KC:XXcm` | Khoảng cách liên tục |

**Nút A** = servo đảo ON (90°), **Nút B** = servo OFF (0°) — test không cần IoT.

Tải trực tiếp từ GitHub (**bắt buộc dùng bản mới — bản cũ trên `main` trước 2026-08-12 bị lỗi trống khối lệnh**):

`https://raw.githubusercontent.com/VuNam1208/Nhung/main/giao-thong-thong-minh.json`

Nếu link trên vẫn trống, thử tải file từ máy tính sau khi `git pull` repo `VuNam1208/Nhung`.

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
| Thời gian đèn xanh | `{GREEN_MS}` ms | Mỗi lượt xanh |
| Thời gian đèn vàng | `{YELLOW_MS}` ms | Mỗi lượt vàng |
| Ngưỡng kẹt xe | `{JAM_DISTANCE_CM}` cm | Siêu âm nhỏ hơn = có xe |
| Thời gian xác nhận kẹt | `{JAM_HOLD_MS}` ms | Giữ ngưỡng bao lâu |
| Servo bình thường | `{SERVO_NORMAL}`° | Làn mặc định |
| Servo đảo chiều | `{SERVO_REVERSE}`° | Mở thêm làn |

## Chế độ bình thường

Hai bộ đèn chạy chu trình:

1. **Xanh 1 – Đỏ 2**
2. **Vàng 1 – Đỏ 2**
3. **Đỏ 1 – Xanh 2**
4. **Đỏ 1 – Vàng 2** → lặp lại

- Hướng 1: ma trận LED trên Yolo:Bit
- Hướng 2: LED RGB ngoài (P0)

## Chế độ kẹt xe & IoT

- Siêu âm < `{JAM_DISTANCE_CM}` cm liên tục `{JAM_HOLD_MS}` ms → gửi **`KET XE!`** lên kênh `{CH_STATUS}`
- Bảng IoT điều khiển:
  - `{CH_GREEN1}`: kéo dài xanh hướng 1
  - `{CH_GREEN2}`: kéo dài xanh hướng 2
  - `{CH_LCD_ROUTE}`: LCD hướng đi vòng tránh
  - `{CH_LCD_LANE}`: LCD cho phép dùng làn chung
  - `{CH_LANE_REV}`: kích hoạt servo đảo làn (`1` = bật, `0` = tắt)
  - `{CH_DISTANCE}`: khoảng cách siêu âm (cm)

Chi tiết bảng IoT: xem **`BANG-IOT-GIAO-THONG.md`**

## Kiểm thử nhanh

1. Chạy chương trình → hai bộ đèn chuyển màu đúng chu trình
2. Đưa tay/tấm bìa gần siêu âm > 5 giây → Bảng IoT báo **KET XE!**
3. Nhấn nút trên IoT → LCD / servo / thời gian xanh thay đổi

## Nộp bài

- File **`giao-thong-thong-minh.json`**
- Ảnh chụp Bảng IoT + Yolo:Bit khi chạy
- Ghi rõ username IoT và các tham số đã chọn
"""


def build_iot_guide() -> str:
    return f"""# Bảng IoT — Giao thông thông minh (Bài tập 2)

## Thông tin chung

| Mục | Giá trị |
|-----|---------|
| Tên bảng | **SMART TRAFFIC** |
| Username | `{IOT_USERNAME}` |
| Server | `mqtt.ohstem.vn` |

## Widget đề xuất

| Widget | Tên hiển thị | Kênh | Chức năng |
|--------|--------------|------|-----------|
| Label | Trạng thái / cảnh báo | **{CH_STATUS}** | Hiện `BINH THUONG` hoặc `KET XE!` |
| Label | Khoảng cách (cm) | **{CH_DISTANCE}** | Yolo:Bit gửi liên tục |
| Nút | Xanh lâu H1 | **{CH_GREEN1}** | Gửi `1` → thêm xanh hướng 1 |
| Nút | Xanh lâu H2 | **{CH_GREEN2}** | Gửi `1` → thêm xanh hướng 2 |
| Nút | Hướng vòng tránh | **{CH_LCD_ROUTE}** | Gửi `1` → LCD đường tránh |
| Nút | Mở làn chung | **{CH_LCD_LANE}** | Gửi `1` → LCD xe máy được đi |
| Nút | Đảo làn BẬT | **{CH_LANE_REV}** | Gửi `1` → servo góc {SERVO_REVERSE}° |
| Nút | Đảo làn TẮT | **{CH_LANE_REV}** | Gửi `0` → servo góc {SERVO_NORMAL}° |

## Cấu hình nút

Mỗi **nút bấm**: **Giá trị gửi khi nhấn** = `1` (riêng nút TẮT đảo làn = `0`).

## Liên kết code

Username trong khối **kết nối server OhStem** phải trùng **`{IOT_USERNAME}`**.

## Kiểm thử

1. Yolo:Bit kết nối WiFi + MQTT thành công
2. Bảng ở chế độ **Play**
3. Gây kẹt xe (che siêu âm) → `{CH_STATUS}` = `KET XE!`
4. Nhấn các nút → LCD / servo / đèn phản hồi
"""


def build_block_guide() -> str:
    return f"""# Khối lệnh — Giao thông thông minh Yolo:Bit

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
Servo P6 → {SERVO_NORMAL}°
LCD: "Giao thong OK" / "San sang"
Khởi tạo siêu âm P10/P13
Kết nối WiFi + MQTT username "{IOT_USERNAME}"
Gửi "BINH THUONG" → {CH_STATUS}
[Đăng ký nhận {CH_GREEN1}..{CH_LANE_REV}]
```

## LẶP LẠI MÃI

```
Kiểm tra tin nhắn MQTT
Nếu siêu âm < {JAM_DISTANCE_CM} cm:
    tăng dem ket xe
    nếu dem ket xe ≥ {JAM_HOLD_MS // LOOP_MS} và chưa báo:
        gửi "KET XE!" → {CH_STATUS}
        LCD cảnh báo
Ngược lại: đặt dem ket xe = 0
Gửi khoảng cách → {CH_DISTANCE}

Chu trình đèn (4 bước, sleep theo tham số):
  0: Xanh1-Đỏ2  → sleep {GREEN_MS} ms
  1: Vàng1-Đỏ2  → sleep {YELLOW_MS} ms
  2: Đỏ1-Xanh2  → sleep {GREEN_MS} ms
  3: Đỏ1-Vàng2  → sleep {YELLOW_MS} ms
```

## MQTT nhận lệnh

| Kênh | Khi nhận `1` |
|------|----------------|
| {CH_GREEN1} | Tăng thời gian xanh hướng 1 |
| {CH_GREEN2} | Tăng thời gian xanh hướng 2 |
| {CH_LCD_ROUTE} | LCD đường vòng tránh |
| {CH_LCD_LANE} | LCD mở làn chung |
| {CH_LANE_REV} | `1` bật đảo làn / `0` tắt |
"""


def validate_python(py: str) -> None:
    required = [
        "aiot_ultrasonic",
        "mqtt.connect_wifi",
        "mqtt.on_receive_message",
        "mqtt.check_message",
        "tiny_rgb.show",
        "display.set_all",
        "pin6.servo_write",
        "doc_khoang_cach",
        "khoi_tao_sieu_am",
        "KET XE!",
        str(GREEN_MS),
        str(JAM_DISTANCE_CM),
    ]
    missing = [k for k in required if k not in py]
    if missing:
        raise SystemExit(f"Python validation failed, missing: {missing}")


def write_project(path: Path, wifi: str, passwd: str, iot_user: str) -> None:
    global WIFI_NAME, WIFI_PASS, IOT_USERNAME
    WIFI_NAME, WIFI_PASS, IOT_USERNAME = wifi, passwd, iot_user
    python = build_python()
    xml = build_xml()
    validate_python(python)
    project = {
        "mode": "python",
        "name": "Giao thong thong minh",
        "device": "yolobit",
        "xmlText": xml,
        "python": python,
        "extensions": EXTENSIONS,
    }
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")


def build_test_sieu_am_xml() -> str:
    return (
        '<xml xmlns="https://developers.google.com/blockly/xml">'
        '<block type="yolobit_basic_forever" id="main" x="20" y="20">'
        '<statement name="ONSTART"></statement>'
        '<statement name="FOREVER"></statement>'
        "</block></xml>"
    )


def build_test_sieu_am_python() -> str:
    return '''from yolobit import *
import time
from aiot_lcd1602 import LCD1602
from aiot_hcsr04 import HCSR04

aiot_lcd1602 = LCD1602()
aiot_ultrasonic = None
khoang_cach = 999

def hien_kc():
  global khoang_cach
  if aiot_ultrasonic is None:
    khoang_cach = 999
  else:
    try:
      khoang_cach = int(aiot_ultrasonic.distance_cm())
    except OSError:
      khoang_cach = 999
  aiot_lcd1602.clear()
  aiot_lcd1602.move_to(0, 0)
  aiot_lcd1602.putstr('Khoang cach')
  aiot_lcd1602.move_to(0, 1)
  aiot_lcd1602.putstr(str(khoang_cach) + ' cm')

aiot_lcd1602.clear()
aiot_lcd1602.move_to(0, 0)
aiot_lcd1602.putstr('Test sieu am')
aiot_lcd1602.move_to(0, 1)
aiot_lcd1602.putstr('P10/P13')
time.sleep_ms(800)
aiot_ultrasonic = HCSR04(trigger_pin=pin10.pin, echo_pin=pin13.pin)
time.sleep_ms(500)

while True:
  hien_kc()
  time.sleep_ms(200)
'''


def write_test_sieu_am(path: Path) -> None:
    project = {
        "mode": "python",
        "name": "Test sieu am",
        "device": "yolobit",
        "xmlText": build_test_sieu_am_xml(),
        "python": build_test_sieu_am_python(),
        "extensions": [EXTENSIONS[0]],
    }
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_xml(xml: str) -> None:
    if "yolobit_basic_forever" not in xml:
        raise SystemExit("XML missing yolobit_basic_forever block")


def main() -> None:
    write_project(OUTPUT, WIFI_NAME, WIFI_PASS, IOT_USERNAME)
    write_test_sieu_am(OUTPUT_TEST)

    GUIDE.write_text(build_guide(), encoding="utf-8")
    BLOCK_GUIDE.write_text(build_block_guide(), encoding="utf-8")
    IOT_GUIDE.write_text(build_iot_guide(), encoding="utf-8")

    xml = json.loads(OUTPUT.read_text())["xmlText"]
    validate_xml(xml)
    assert "yolobit_basic_forever" in xml
    assert "doc_khoang_cach" in json.loads(OUTPUT.read_text())["python"]
    print("Created", OUTPUT)
    print("Created", OUTPUT_TEST)
    print("Created", GUIDE, BLOCK_GUIDE, IOT_GUIDE)


if __name__ == "__main__":
    main()
