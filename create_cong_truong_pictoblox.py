#!/usr/bin/env python3
"""PictoBlox Stage Mode: Cong truong an toan + Camera AI + Arduino."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

STAGE_TEMPLATE = Path(
    "/tmp/uno/sunfounder-uno-and-mega-kit-master/scratch(uno)/code/1. Stage Mode.sb3"
)
OUTPUT = Path(__file__).with_name("cong-truong-an-toan-pictoblox.sb3")

XE = {"do": "2", "vang": "3", "xanh": "4"}
NGUOI = {"do": "5", "vang": "6", "xanh": "7"}
BUZZER, LED_BAO, SERVO = "8", "9", "10"
TRIG, ECHO, IR_PIN = "11", "12", "A0"
LCD_ADDR = "0x27"

MODEL_URL = "https://teachablemachine.withgoogle.com/models/YOUR_MODEL_ID/"
CLASS_HS = "Hoc sinh"
VAR_AI = ("co_hs_ai", "var_co_hs_ai")


class B:
    def __init__(self) -> None:
        self.blocks: dict[str, dict] = {}
        self.n = 0

    def nid(self, p: str = "b") -> str:
        self.n += 1
        return f"{p}{self.n}"

    def add(
        self,
        opcode: str,
        *,
        parent: str | None = None,
        inputs: dict | None = None,
        fields: dict | None = None,
        top: bool = False,
        shadow: bool = False,
        prefix: str = "b",
    ) -> str:
        bid = self.nid(prefix)
        blk = {
            "opcode": opcode,
            "next": None,
            "parent": parent,
            "inputs": inputs or {},
            "fields": fields or {},
            "shadow": shadow,
            "topLevel": top,
        }
        if top:
            blk["x"] = 60
            blk["y"] = 40
        self.blocks[bid] = blk
        return bid

    def link(self, *ids: str) -> str:
        for a, c in zip(ids, ids[1:]):
            self.blocks[a]["next"] = c
            self.blocks[c]["parent"] = a
        return ids[-1]

    def num(self, v: str | int | float) -> list:
        return [1, [4, str(v)]]

    def txt(self, v: str) -> list:
        return [1, [10, v]]

    def var_ref(self, name: str, vid: str, parent: str) -> str:
        return self.add(
            "data_variable",
            parent=parent,
            fields={"VARIABLE": [name, vid]},
            prefix="vr",
        )

    def set_var(self, name: str, vid: str, value: int) -> str:
        return self.add(
            "data_setvariableto",
            fields={"VARIABLE": [name, vid]},
            inputs={"VALUE": self.num(value)},
            prefix="sv",
        )

    def var_is_one(self, parent: str) -> str:
        eq = self.add("operator_equals", parent=parent, prefix="eq")
        ref = self.var_ref(VAR_AI[0], VAR_AI[1], eq)
        self.blocks[eq]["inputs"] = {
            "OPERAND1": [2, ref],
            "OPERAND2": self.num(1),
        }
        return eq

    def wait(self, sec: str) -> str:
        return self.add("control_wait", inputs={"DURATION": self.num(sec)}, prefix="w")

    def pin_out(self, pin: str, high: bool) -> str:
        return self.add(
            "arduinoUno_digitalWrite",
            fields={"PIN": [pin, None], "MODE": ["true" if high else "false", None]},
            prefix="po",
        )

    def servo(self, angle: str) -> str:
        return self.add(
            "actuators_setServoOnPinToAngle",
            fields={"PIN": [SERVO, None], "ANGLE": [angle, None]},
            prefix="svo",
        )

    def lcd_init(self) -> str:
        return self.link(
            self.add(
                "displayModule_initialiseI2CDisplay",
                inputs={"I2C_ADD": self.num(LCD_ADDR)},
                prefix="lcd",
            ),
            self.add("displayModule_clearDisplay", prefix="lcd"),
        )

    def lcd_text(self, row: str, col: str, text: str) -> str:
        return self.link(
            self.add(
                "displayModule_setCursor",
                fields={"ROW": [row, None], "COLUMN": [col, None]},
                prefix="lcd",
            ),
            self.add("displayModule_write", inputs={"TEXT": self.txt(text)}, prefix="lcd"),
        )

    def set_xe(self, do: bool, vang: bool, xanh: bool) -> str:
        return self.link(
            self.pin_out(XE["do"], do),
            self.pin_out(XE["vang"], vang),
            self.pin_out(XE["xanh"], xanh),
        )

    def set_nguoi(self, do: bool, vang: bool, xanh: bool) -> str:
        return self.link(
            self.pin_out(NGUOI["do"], do),
            self.pin_out(NGUOI["vang"], vang),
            self.pin_out(NGUOI["xanh"], xanh),
        )

    def sensor_ok(self) -> str:
        ir = self.add(
            "arduinoUno_digitalRead",
            fields={"PIN": [IR_PIN, None]},
            prefix="ir",
        )
        eq = self.add("operator_equals", prefix="eq")
        self.blocks[eq]["inputs"] = {
            "OPERAND1": [2, ir],
            "OPERAND2": [1, [10, "false"]],
        }
        us = self.add(
            "sensors_readUltrasonic",
            fields={"TRIG_PIN": [TRIG, None], "ECHO_PIN": [ECHO, None]},
            prefix="us",
        )
        gt = self.add("operator_gt", prefix="gt")
        self.blocks[gt]["inputs"] = {
            "OPERAND1": [3, us, self.num(0)],
            "OPERAND2": self.num(30),
        }
        both = self.add("operator_and", prefix="and")
        self.blocks[both]["inputs"] = {
            "OPERAND1": [2, eq],
            "OPERAND2": [2, gt],
        }
        return both

    def full_condition(self) -> str:
        ai = self.var_is_one(None)
        sen = self.sensor_ok()
        both = self.add("operator_and", prefix="and")
        self.blocks[both]["inputs"] = {
            "OPERAND1": [2, ai],
            "OPERAND2": [2, sen],
        }
        return both

    def binh_thuong(self) -> str:
        return self.link(
            self.set_xe(False, False, True),
            self.set_nguoi(True, False, False),
            self.servo("90"),
            self.pin_out(BUZZER, False),
            self.pin_out(LED_BAO, False),
            self.lcd_text("1", "1", "Xe: XANH"),
            self.lcd_text("2", "1", "HS: DUNG"),
        )

    def sang_duong(self) -> str:
        return self.link(
            self.set_xe(True, False, False),
            self.set_nguoi(False, False, True),
            self.servo("0"),
            self.pin_out(BUZZER, True),
            self.pin_out(LED_BAO, True),
            self.lcd_text("1", "1", "HS SANG!"),
            self.lcd_text("2", "1", "AI OK"),
            self.wait("5"),
            self.pin_out(BUZZER, False),
            self.pin_out(LED_BAO, False),
            self.servo("90"),
            self.wait("1"),
        )


def build_camera_ai_sprite() -> dict:
    b = B()
    flag = b.add("event_whenflagclicked", top=True, prefix="f")
    use = b.add(
        "teachableMachine_useModelBlock",
        inputs={"MODEL_URL": b.txt(MODEL_URL)},
        prefix="tm",
    )
    von = b.add("teachableMachine_videoToggle", prefix="tm")
    vonm = b.add(
        "teachableMachine_menu_VIDEO_STATE",
        fields={"VIDEO_STATE": ["on", None]},
        shadow=True,
        prefix="tm",
    )
    b.blocks[von]["inputs"] = {"VIDEO_STATE": [1, vonm]}
    trans = b.add(
        "teachableMachine_setVideoTransparency",
        inputs={"TRANSPARENCY": b.num(20)},
        prefix="tm",
    )
    wait = b.add("control_wait", inputs={"DURATION": b.num(3)}, prefix="w")
    b.link(flag, use, von, trans, wait)

    forever = b.add("control_forever", prefix="fr")
    b.link(wait, forever)

    if_yes = b.add("control_if", prefix="if")
    pred_yes = b.add(
        "teachableMachine_modelMatches",
        fields={"CLASS_NAME": [CLASS_HS, None]},
        prefix="tm",
    )
    set1 = b.set_var(VAR_AI[0], VAR_AI[1], 1)
    b.blocks[if_yes]["inputs"] = {
        "CONDITION": [2, pred_yes],
        "SUBSTACK": [2, set1],
    }
    b.blocks[set1]["parent"] = if_yes

    if_no = b.add("control_if", prefix="if")
    pred_no = b.add(
        "teachableMachine_modelMatches",
        fields={"CLASS_NAME": [CLASS_HS, None]},
        prefix="tm",
    )
    not_pred = b.add("operator_not", prefix="nt")
    b.blocks[not_pred]["inputs"] = {"OPERAND": [2, pred_no]}
    set0 = b.set_var(VAR_AI[0], VAR_AI[1], 0)
    b.blocks[if_no]["inputs"] = {
        "CONDITION": [2, not_pred],
        "SUBSTACK": [2, set0],
    }
    b.blocks[set0]["parent"] = if_no

    delay = b.wait("0.2")
    b.link(if_yes, if_no, delay)
    b.blocks[forever]["inputs"] = {"SUBSTACK": [2, if_yes]}
    b.blocks[if_yes]["parent"] = forever

    return b.blocks


def build_arduino_sprite() -> dict:
    b = B()
    flag = b.add("event_whenflagclicked", top=True, prefix="f")
    init = b.lcd_init()
    t1 = b.lcd_text("1", "1", "Cong Truong AT")
    t2 = b.lcd_text("2", "1", "Smart Crossing")
    b.link(flag, init, t1, t2)

    forever = b.add("control_forever", prefix="fr")
    b.link(t2, forever)

    normal = b.binh_thuong()
    if_id = b.add("control_if", prefix="if")
    cond = b.full_condition()
    cross = b.sang_duong()
    b.blocks[if_id]["inputs"] = {
        "CONDITION": [2, cond],
        "SUBSTACK": [2, cross],
    }
    b.blocks[cross]["parent"] = if_id
    pause = b.wait("0.3")
    b.link(normal, if_id, pause)
    b.blocks[forever]["inputs"] = {"SUBSTACK": [2, normal]}
    b.blocks[normal]["parent"] = forever

    return b.blocks


def main() -> None:
    if not STAGE_TEMPLATE.exists():
        raise SystemExit(f"Missing template: {STAGE_TEMPLATE}")

    with zipfile.ZipFile(STAGE_TEMPLATE, "r") as zin:
        base = json.loads(zin.read("project.json"))

    stage = base["targets"][0]
    tpl = base["targets"][1]
    stage["variables"] = {VAR_AI[1]: [VAR_AI[0], 0]}
    stage["blocks"] = {}

    cam = json.loads(json.dumps(tpl))
    cam["name"] = "Camera AI"
    cam["blocks"] = build_camera_ai_sprite()

    ard = json.loads(json.dumps(tpl))
    ard["name"] = "Arduino Gate"
    ard["blocks"] = build_arduino_sprite()

    project = base
    project["extensions"] = [
        "arduinoUno",
        "sensors",
        "displayModule",
        "actuators",
        "teachableMachine",
    ]
    project["meta"]["agent"] = "cong-truong-an-toan-ai"
    project["targets"] = [stage, cam, ard]

    data = json.dumps(project, ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(STAGE_TEMPLATE, "r") as zin, zipfile.ZipFile(OUTPUT, "w") as zout:
        for item in zin.infolist():
            zout.writestr(item, data if item.filename == "project.json" else zin.read(item.filename))

    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()
