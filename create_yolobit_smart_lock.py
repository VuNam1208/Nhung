#!/usr/bin/env python3
"""Generate OhStem Yolo:Bit project: Smart lock with LCD1602, RGB LED and IoT panel."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

OUTPUT = Path(__file__).with_name("o-khoa-yolo-bit.json")
GUIDE = Path(__file__).with_name("HUONG-DAN-O-KHOA-YOLOBIT.md")

# --- User configuration (edit before flashing) ---
WIFI_NAME = "TenWiFi"
WIFI_PASS = "MatKhauWiFi"
IOT_USERNAME = "SmartKey123"
DEFAULT_PASSWORD = "1221"
MAX_WRONG = 3

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

# MQTT channels used by the IoT panel (SMART KEY)
CH_STATUS = "V1"  # Hiển thị mật khẩu / trạng thái
CH_UNLOCK = "V2"  # Mở khóa từ xa
CH_RESET = "V3"  # Tạo mật khẩu mới
CH_CHAR1 = "V4"  # Nút 1
CH_CHAR2 = "V5"  # Nút 2
CH_SAVE = "V6"  # Lưu mật khẩu mới
CH_ALERT = "V7"  # Cảnh báo khóa hệ thống


def _uid() -> str:
    return uuid.uuid4().hex[:12]


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

    def btn_pressed(self, which: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="yolobit_input_button_is_pressed" id="{bid}">'
            f'<field name="button">{which}</field></block>'
        )

    def chain(self, *blocks: str) -> str:
        if not blocks:
            return ""
        if len(blocks) == 1:
            return blocks[0]
        result = blocks[0]
        for nxt in blocks[1:]:
            idx = result.rfind("</block>")
            result = result[:idx] + f"<next>{nxt}</next>" + result[idx:]
        return result

    def stmt_if(self, cond: str, do: str, else_do: str | None = None, bid: str | None = None) -> str:
        bid = bid or self.bid()
        mut = '<mutation else="1"></mutation>' if else_do else ""
        else_part = f'<statement name="ELSE">{else_do}</statement>' if else_do else ""
        return (
            f'<block type="controls_if" id="{bid}">{mut}'
            f'<value name="IF0">{cond}</value>'
            f'<statement name="DO0">{do}</statement>{else_part}</block>'
        )

    def lcd_show(self, text_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        clear_id = self.bid()
        disp_id = self.bid()
        clear = f'<block type="aiot_lcd1602_clear" id="{clear_id}"></block>'
        disp = (
            f'<block type="aiot_lcd1602_display" id="{disp_id}">'
            f'<value name="string">{text_xml}</value>'
            f'<value name="X">{self.num(0)}</value>'
            f'<value name="Y">{self.num(0)}</value></block>'
        )
        return self.chain(clear, disp)

    def sleep_ms(self, ms: int, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="yolobit_basic_sleep" id="{bid}">'
            f'<value name="duration">{self.num(ms)}</value></block>'
        )

    def play_note(self, bid: str | None = None) -> str:
        bid = bid or self.bid()
        pitch = self.bid()
        return (
            f'<block type="yolobit_music_play_note" id="{bid}"><field name="DURATION">1</field>'
            f'<value name="PITCH"><shadow type="yolobit_music_note" id="{pitch}">'
            f'<field name="PITCH">7</field></shadow></value></block>'
        )

    def play_melody(self, melody: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="yolobit_music_play_built_in_until_done" id="{bid}">'
            f'<field name="melody">{melody}</field></block>'
        )

    def rgb(self, colour: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        sh = self.bid()
        return (
            f'<block type="aiot_led_tiny_set_all" id="{bid}">'
            f'<field name="port">pin0</field><field name="option">0</field>'
            f'<value name="COLOR"><shadow type="colour_picker" id="{sh}">'
            f'<field name="COLOUR">{colour}</field></shadow></value></block>'
        )

    def math_add(self, a_xml: str, b_xml: str, bid: str | None = None) -> str:
        bid = bid or self.bid()
        return (
            f'<block type="math_arithmetic" id="{bid}"><field name="OP">ADD</field>'
            f'<value name="A">{a_xml}</value><value name="B">{b_xml}</value></block>'
        )

    def increment_var(self, var_id: str, name: str) -> str:
        return self.var_set(
            var_id,
            name,
            self.math_add(self.var_get(var_id, name), self.num(1)),
        )
        join_id = self.bid()
        return self.var_set(
            var_id,
            var_name,
            (
                f'<block type="text_join" id="{join_id}"><mutation items="2"></mutation>'
                f'<value name="ADD0">{self.var_get(var_id, var_name)}</value>'
                f'<value name="ADD1">{self.text(ch)}</value></block>'
            ),
        )

    def servo_open(self) -> str:
        b1 = self.bid()
        b2 = self.bid()
        b3 = self.bid()
        s1 = (
            f'<block type="yolobit_pin_servo_write_angle" id="{b1}"><field name="pin">6</field>'
            f'<value name="angle">{self.num(90)}</value></block>'
        )
        sl = (
            f'<block type="yolobit_basic_sleep" id="{b2}">'
            f'<value name="duration">{self.num(2000)}</value></block>'
        )
        s0 = (
            f'<block type="yolobit_pin_servo_write_angle" id="{b3}"><field name="pin">6</field>'
            f'<value name="angle">{self.num(0)}</value></block>'
        )
        rel = (
            f'<block type="yolobit_pin_servo_release" id="{self.bid()}">'
            f'<field name="pin">6</field></block>'
        )
        return self.chain(s1, sl, s0, rel)

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
import music
import time
from mqtt import *
from aiot_lcd1602 import LCD1602
from aiot_rgbled import RGBLed

button_a.on_pressed = None
button_b.on_pressed = None
button_a.on_pressed_ab = button_b.on_pressed_ab = -1

aiot_lcd1602 = LCD1602()
tiny_rgb = RGBLed(pin0.pin, 4)

WIFI_NAME = '{WIFI_NAME}'
WIFI_PASS = '{WIFI_PASS}'
IOT_USER = '{IOT_USERNAME}'
MAX_SAI = {MAX_WRONG}

mat_khau_cai_dat = '{DEFAULT_PASSWORD}'
mat_khau_nhap = ''
dem_sai = 0
khoa_vat_ly = 0
dang_reset_mk = 0
mk_moi = ''

def hien_lcd(msg):
  aiot_lcd1602.clear()
  aiot_lcd1602.move_to(0, 0)
  aiot_lcd1602.putstr(str(msg)[:16])

def rgb(mau):
  tiny_rgb.show(0, hex_to_rgb(mau))

def dem_ky_tu_khac(s):
  d = {{}}
  for c in str(s):
    d[c] = 1
  return len(d)

def mo_khoa():
  global dem_sai, mat_khau_nhap
  hien_lcd('Mo khoa OK!')
  rgb('#00ff00')
  music.play(music.POWER_UP, wait=True)
  pin6.servo_write(90)
  time.sleep_ms(2000)
  pin6.servo_write(0)
  pin6.servo_release()
  dem_sai = 0
  mat_khau_nhap = ''
  rgb('#000000')

def khoa_he_thong():
  global khoa_vat_ly
  khoa_vat_ly = 1
  hien_lcd('He thong khoa!')
  rgb('#ff0000')
  mqtt.publish('{CH_ALERT}', 'KHOA: Sai qua nhieu lan')
  mqtt.publish('{CH_STATUS}', mat_khau_cai_dat)

def sai_mat_khau():
  global dem_sai, mat_khau_nhap
  dem_sai += 1
  hien_lcd('Sai ' + str(dem_sai) + '/' + str(MAX_SAI))
  rgb('#ff0000')
  music.play(music.POWER_DOWN, wait=True)
  mat_khau_nhap = ''
  if dem_sai >= MAX_SAI:
    khoa_he_thong()

def kiem_tra_mk():
  global mat_khau_nhap
  if mat_khau_nhap == mat_khau_cai_dat:
    mo_khoa()
  else:
    sai_mat_khau()

def luu_mk_moi():
  global mat_khau_cai_dat, mk_moi, dang_reset_mk, dem_sai, khoa_vat_ly
  if len(mk_moi) < 4 or dem_ky_tu_khac(mk_moi) < 2:
    mqtt.publish('{CH_STATUS}', 'Loi: >=4 ky tu')
    hien_lcd('MK khong hop le')
    rgb('#ff0000')
    music.play(music.POWER_DOWN, wait=True)
    return
  mat_khau_cai_dat = mk_moi
  mk_moi = ''
  dang_reset_mk = 0
  dem_sai = 0
  khoa_vat_ly = 0
  mqtt.publish('{CH_STATUS}', mat_khau_cai_dat)
  mqtt.publish('{CH_ALERT}', 'Da luu MK moi')
  hien_lcd('Luu MK OK')
  rgb('#00ff00')
  music.play(music.POWER_UP, wait=True)
  time.sleep_ms(800)
  rgb('#000000')

def on_{CH_UNLOCK.lower()}(thong_tin):
  global khoa_vat_ly
  if khoa_vat_ly:
    return
  if str(thong_tin) in ('1', 'MO', 'mo'):
    mo_khoa()

def on_{CH_RESET.lower()}(thong_tin):
  global dang_reset_mk, mk_moi
  if str(thong_tin) in ('1', 'RESET', 'reset'):
    dang_reset_mk = 1
    mk_moi = ''
    mqtt.publish('{CH_STATUS}', '')
    hien_lcd('Nhap MK moi')

def on_{CH_CHAR1.lower()}(thong_tin):
  global mk_moi, dang_reset_mk
  if dang_reset_mk:
    mk_moi = str(mk_moi) + '1'
    mqtt.publish('{CH_STATUS}', mk_moi)

def on_{CH_CHAR2.lower()}(thong_tin):
  global mk_moi, dang_reset_mk
  if dang_reset_mk:
    mk_moi = str(mk_moi) + '2'
    mqtt.publish('{CH_STATUS}', mk_moi)

def on_{CH_SAVE.lower()}(thong_tin):
  global dang_reset_mk
  if dang_reset_mk and str(thong_tin) in ('1', 'LUU', 'luu'):
    luu_mk_moi()

if True:
  mat_khau_cai_dat = '{DEFAULT_PASSWORD}'
  mat_khau_nhap = ''
  dem_sai = 0
  khoa_vat_ly = 0
  dang_reset_mk = 0
  mk_moi = ''
  hien_lcd('Nhap MK')
  rgb('#000000')
  mqtt.connect_wifi(WIFI_NAME, WIFI_PASS)
  mqtt.connect_broker(server='mqtt.ohstem.vn', port=1883, username=IOT_USER, password='')
  mqtt.on_receive_message('{CH_UNLOCK}', on_{CH_UNLOCK.lower()})
  mqtt.on_receive_message('{CH_RESET}', on_{CH_RESET.lower()})
  mqtt.on_receive_message('{CH_CHAR1}', on_{CH_CHAR1.lower()})
  mqtt.on_receive_message('{CH_CHAR2}', on_{CH_CHAR2.lower()})
  mqtt.on_receive_message('{CH_SAVE}', on_{CH_SAVE.lower()})
  mqtt.publish('{CH_STATUS}', mat_khau_cai_dat)

while True:
  mqtt.check_message()
  if not khoa_vat_ly:
    if button_a.is_pressed_ab():
      kiem_tra_mk()
      time.sleep_ms(400)
    elif button_a.is_pressed():
      music.play(['G3:1'], wait=True)
      mat_khau_nhap = str(mat_khau_nhap) + '1'
      hien_lcd(mat_khau_nhap)
      time.sleep_ms(250)
    elif button_b.is_pressed():
      music.play(['G3:1'], wait=True)
      mat_khau_nhap = str(mat_khau_nhap) + '2'
      hien_lcd(mat_khau_nhap)
      time.sleep_ms(250)
  time.sleep_ms(80)
'''


def build_xml() -> str:
    x = Xml()
    v_mk = "vMKset"
    v_in = "vMKin"
    v_sai = "vSai"
    v_lock = "vLock"
    v_reset = "vResetMode"
    v_new = "vNewMK"
    v_msg = "vMsg"

    unlock_ok = x.chain(
        x.lcd_show(x.text("Mo khoa OK!")),
        x.rgb("#00ff00"),
        x.play_melody("POWER_UP"),
        x.servo_open(),
        x.var_set(v_sai, "dem sai", x.num(0)),
        x.var_set(v_in, "mat khau nhap", x.text("")),
        x.rgb("#000000"),
    )

    wrong_body = x.chain(
        x.increment_var(v_sai, "dem sai"),
        x.lcd_show(x.text("Sai mat khau")),
        x.rgb("#ff0000"),
        x.play_melody("POWER_DOWN"),
        x.var_set(v_in, "mat khau nhap", x.text("")),
        x.stmt_if(
            x.compare_gte(x.var_get(v_sai, "dem sai"), x.num(MAX_WRONG)),
            x.chain(
                x.var_set(v_lock, "khoa vat ly", x.num(1)),
                x.lcd_show(x.text("He thong khoa!")),
                x.mqtt_publish(CH_ALERT, x.text("KHOA: Sai qua nhieu lan")),
                x.mqtt_publish(CH_STATUS, x.var_get(v_mk, "mat khau cai dat")),
            ),
        ),
    )

    check_pw = x.stmt_if(
        x.compare_eq(x.var_get(v_in, "mat khau nhap"), x.var_get(v_mk, "mat khau cai dat")),
        unlock_ok,
        wrong_body,
    )

    press_a = x.chain(
        x.play_note(),
        x.append_char(v_in, "mat khau nhap", "1"),
        x.lcd_show(x.var_get(v_in, "mat khau nhap")),
        x.sleep_ms(250),
    )

    press_b = x.chain(
        x.play_note(),
        x.append_char(v_in, "mat khau nhap", "2"),
        x.lcd_show(x.var_get(v_in, "mat khau nhap")),
        x.sleep_ms(250),
    )

    not_locked = x.logic_not(x.compare_eq(x.var_get(v_lock, "khoa vat ly"), x.num(1)))

    forever = x.chain(
        x.mqtt_check(),
        x.stmt_if(
            not_locked,
            x.stmt_if(
                x.btn_pressed("a+b"),
                check_pw,
                x.stmt_if(
                    x.btn_pressed("a"),
                    press_a,
                    x.stmt_if(x.btn_pressed("b"), press_b),
                ),
            ),
        ),
        x.sleep_ms(80),
    )

    mqtt_callbacks = x.chain(
        x.mqtt_on_receive(
            CH_UNLOCK,
            v_msg,
            "thong tin",
            x.stmt_if(
                x.logic_and(
                    x.logic_not(x.compare_eq(x.var_get(v_lock, "khoa vat ly"), x.num(1))),
                    x.compare_eq(x.var_get(v_msg, "thong tin"), x.text("1")),
                ),
                unlock_ok,
            ),
        ),
        x.mqtt_on_receive(
            CH_RESET,
            v_msg,
            "thong tin",
            x.stmt_if(
                x.compare_eq(x.var_get(v_msg, "thong tin"), x.text("1")),
                x.chain(
                    x.var_set(v_reset, "dang reset mk", x.num(1)),
                    x.var_set(v_new, "mk moi", x.text("")),
                    x.mqtt_publish(CH_STATUS, x.text("")),
                    x.lcd_show(x.text("Nhap MK moi")),
                ),
            ),
        ),
        x.mqtt_on_receive(
            CH_CHAR1,
            v_msg,
            "thong tin",
            x.stmt_if(
                x.compare_eq(x.var_get(v_reset, "dang reset mk"), x.num(1)),
                x.chain(
                    x.var_set(
                        v_new,
                        "mk moi",
                        f'<block type="text_join" id="{x.bid()}"><mutation items="2"></mutation>'
                        f'<value name="ADD0">{x.var_get(v_new, "mk moi")}</value>'
                        f'<value name="ADD1">{x.text("1")}</value></block>',
                    ),
                    x.mqtt_publish(CH_STATUS, x.var_get(v_new, "mk moi")),
                ),
            ),
        ),
        x.mqtt_on_receive(
            CH_CHAR2,
            v_msg,
            "thong tin",
            x.stmt_if(
                x.compare_eq(x.var_get(v_reset, "dang reset mk"), x.num(1)),
                x.chain(
                    x.var_set(
                        v_new,
                        "mk moi",
                        f'<block type="text_join" id="{x.bid()}"><mutation items="2"></mutation>'
                        f'<value name="ADD0">{x.var_get(v_new, "mk moi")}</value>'
                        f'<value name="ADD1">{x.text("2")}</value></block>',
                    ),
                    x.mqtt_publish(CH_STATUS, x.var_get(v_new, "mk moi")),
                ),
            ),
        ),
        x.mqtt_on_receive(
            CH_SAVE,
            v_msg,
            "thong tin",
            x.stmt_if(
                x.logic_and(
                    x.compare_eq(x.var_get(v_reset, "dang reset mk"), x.num(1)),
                    x.compare_eq(x.var_get(v_msg, "thong tin"), x.text("1")),
                ),
                x.chain(
                    x.var_set(v_mk, "mat khau cai dat", x.var_get(v_new, "mk moi")),
                    x.var_set(v_new, "mk moi", x.text("")),
                    x.var_set(v_reset, "dang reset mk", x.num(0)),
                    x.var_set(v_sai, "dem sai", x.num(0)),
                    x.var_set(v_lock, "khoa vat ly", x.num(0)),
                    x.mqtt_publish(CH_STATUS, x.var_get(v_mk, "mat khau cai dat")),
                    x.lcd_show(x.text("Luu MK OK")),
                    x.rgb("#00ff00"),
                    x.play_melody("POWER_UP"),
                ),
            ),
        ),
    )

    onstart = x.chain(
        x.var_set(v_mk, "mat khau cai dat", x.text(DEFAULT_PASSWORD)),
        x.var_set(v_in, "mat khau nhap", x.text("")),
        x.var_set(v_sai, "dem sai", x.num(0)),
        x.var_set(v_lock, "khoa vat ly", x.num(0)),
        x.var_set(v_reset, "dang reset mk", x.num(0)),
        x.var_set(v_new, "mk moi", x.text("")),
        x.lcd_show(x.text("Nhap MK")),
        x.rgb("#000000"),
        x.mqtt_wifi(),
        x.mqtt_broker(),
        mqtt_callbacks,
        x.mqtt_publish(CH_STATUS, x.var_get(v_mk, "mat khau cai dat")),
    )

    fb = x.bid()
    return (
        '<xml xmlns="https://developers.google.com/blockly/xml">'
        "<variables>"
        f'<variable id="{v_mk}">mat khau cai dat</variable>'
        f'<variable id="{v_in}">mat khau nhap</variable>'
        f'<variable id="{v_sai}">dem sai</variable>'
        f'<variable id="{v_lock}">khoa vat ly</variable>'
        f'<variable id="{v_reset}">dang reset mk</variable>'
        f'<variable id="{v_new}">mk moi</variable>'
        f'<variable id="{v_msg}">thong tin</variable>'
        "</variables>"
        f'<block type="yolobit_basic_forever" id="{fb}" x="20" y="20">'
        f"<statement name=\"ONSTART\">{onstart}</statement>"
        f'<statement name="FOREVER">{forever}</statement>'
        "</block></xml>"
    )


def build_guide() -> str:
    return f"""# Hướng dẫn: Ổ khóa Yolo:Bit (Bài tập 1)

## Tải chương trình

1. Mở [https://app.ohstem.vn/](https://app.ohstem.vn/)
2. Chọn **Lập trình Yolo:Bit**
3. Menu **Quản lý chương trình** → **Import project**
4. Chọn file **`o-khoa-yolo-bit.json`**
5. Vào **Mở rộng** → cài **AIOT Kit** và **MQTT** (nếu chưa có)
6. Sửa WiFi / username IoT trong khối lệnh hoặc tab MicroPython:
   - WiFi: `{WIFI_NAME}` / `{WIFI_PASS}`
   - Username Bảng IoT: `{IOT_USERNAME}`
7. Kết nối Yolo:Bit → **Chạy** → **Lưu project vào thiết bị**

Tải trực tiếp từ GitHub (nhánh `cursor/yolobit-smart-lock-6e7f`):

`https://github.com/VuNam1208/Nhung/raw/cursor/yolobit-smart-lock-6e7f/o-khoa-yolo-bit.json`

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
- Mật khẩu mặc định: `{DEFAULT_PASSWORD}`
- Sai tối đa **{MAX_WRONG}** lần → khóa nhập bằng nút, báo lên Bảng IoT

### Phản hồi khi kiểm tra

- **Đúng**: LCD *Mo khoa OK!*, nhạc POWER_UP, RGB xanh, Servo mở 2 giây
- **Sai**: LCD *Sai mat khau*, nhạc POWER_DOWN, RGB đỏ

## Tạo Bảng IoT (SMART KEY)

1. OhStem App → **Bảng điều khiển IoT** → Tạo bảng mới
2. Đặt **Username** (ví dụ `{IOT_USERNAME}`) — phải trùng code
3. Kéo widget và gán **kênh MQTT**:

| Widget trên bảng | Kênh | Chức năng |
|------------------|------|-----------|
| Nút *Tạo MK mới* | `{CH_RESET}` | Bắt đầu nhập mật khẩu mới |
| Ô *Mật khẩu hiện tại* | `{CH_STATUS}` | Hiển thị MK / MK đang nhập |
| Nút *1* | `{CH_CHAR1}` | Thêm ký tự 1 |
| Nút *2* | `{CH_CHAR2}` | Thêm ký tự 2 |
| Nút *Lưu* | `{CH_SAVE}` | Lưu mật khẩu mới |
| (Tuỳ chọn) Nút mở khóa | `{CH_UNLOCK}` | Mở khóa từ xa |
| (Tuỳ chọn) Nhãn cảnh báo | `{CH_ALERT}` | Thông báo khi bị khóa |

4. Với mỗi **nút**, trong cài đặt widget chọn **Gửi giá trị** = `1` khi nhấn.

### Reset mật khẩu qua IoT (khi bị khóa)

1. Nhấn **Tạo MK mới** trên bảng
2. Nhấn **1** / **2** để ghép mật khẩu mới (tối thiểu 4 ký tự, ít nhất 2 ký tự khác nhau)
3. Xem trên ô **Mật khẩu hiện tại**
4. Nhấn **Lưu** → hệ thống mở khóa và dùng mật khẩu mới

## Kiểm thử nhanh

1. Nhập `1221` bằng A→1, B→2, A→1 rồi **A+B** → cửa mở
2. Nhập sai `{MAX_WRONG}` lần → LCD *He thong khoa!*, không nhập thêm bằng nút
3. Trên Bảng IoT: Tạo MK mới → nhập `1212` → Lưu → thử mở bằng mật khẩu mới

## Lưu ý nộp bài

- Nộp file **`o-khoa-yolo-bit.json`** hoặc link chia sẻ project OhStem
- Chụp màn hình Bảng IoT + Yolo:Bit khi chạy thử
- Ghi rõ Username IoT và mật khẩu WiFi đã cấu hình
"""


def validate_python(py: str) -> None:
    required = [
        "button_a.is_pressed_ab",
        "mqtt.connect_wifi",
        "mqtt.on_receive_message",
        "tiny_rgb.show",
        "aiot_lcd1602",
        "pin6.servo_write",
        "dem_sai",
        "khoa_vat_ly",
        DEFAULT_PASSWORD,
    ]
    missing = [k for k in required if k not in py]
    if missing:
        raise SystemExit(f"Python validation failed, missing: {missing}")


def main() -> None:
    python = build_python()
    xml = build_xml()
    validate_python(python)

    project = {
        "mode": "block",
        "name": "O khoa YoloBit",
        "device": "yolobit",
        "xmlText": xml,
        "python": python,
        "extensions": EXTENSIONS,
    }

    OUTPUT.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    GUIDE.write_text(build_guide(), encoding="utf-8")

    assert "<block type=\"yolobit_basic_forever\"" in xml
    assert "yolobit_mqtt_connect_wifi" in xml
    assert "aiot_led_tiny_set_all" in xml
    print("Created", OUTPUT)
    print("Created", GUIDE)
    print("XML size:", len(xml), "Python size:", len(python))


if __name__ == "__main__":
    main()
