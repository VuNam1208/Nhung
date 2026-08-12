#!/usr/bin/env python3
"""Generate PictoBlox Upload Mode project: Smart School Crossing full model."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

TEMPLATE = Path(
    "/tmp/uno/sunfounder-uno-and-mega-kit-master/scratch(uno)/code/1. Upload Mode.sb3"
)
OUTPUT = Path(__file__).with_name("smart-school-crossing-pictoblox.sb3")

XE = {"do": "2", "vang": "3", "xanh": "4"}
NGUOI = {"do": "5", "vang": "6", "xanh": "7"}
BUZZER, LED_BAO, SERVO, TRIG, ECHO, IR_PIN = "8", "9", "10", "11", "12", "A0"
LCD_ADDR = "0x27"


class B:
    def __init__(self) -> None:
        self.blocks: dict[str, dict] = {}
        self.n = 0

    def id(self, p: str = "b") -> str:
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
        prefix: str = "b",
    ) -> str:
        bid = self.id(prefix)
        self.blocks[bid] = {
            "opcode": opcode,
            "next": None,
            "parent": parent,
            "inputs": inputs or {},
            "fields": fields or {},
            "shadow": False,
            "topLevel": top,
        }
        if top:
            self.blocks[bid]["x"] = 80
            self.blocks[bid]["y"] = 40
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

    def wait(self, sec: str) -> str:
        return self.add("control_wait", inputs={"DURATION": self.num(sec)}, prefix="w")

    def pin_out(self, pin: str, high: bool) -> str:
        return self.add(
            "arduinoUno_digitalWrite",
            fields={"PIN": [pin, None], "MODE": ["true" if high else "false", None]},
            prefix="p",
        )

    def servo(self, angle: str) -> str:
        return self.add(
            "actuators_setServoOnPinToAngle",
            fields={"PIN": [SERVO, None], "ANGLE": [angle, None]},
            prefix="sv",
        )

    def lcd_init(self) -> str:
        i = self.add(
            "displayModule_initialiseI2CDisplay",
            inputs={"I2C_ADD": self.num(LCD_ADDR)},
            prefix="lcd",
        )
        c = self.add("displayModule_clearDisplay", prefix="lcd")
        return self.link(i, c)

    def lcd_text(self, row: str, col: str, text: str) -> str:
        cur = self.add(
            "displayModule_setCursor",
            fields={"ROW": [row, None], "COLUMN": [col, None]},
            prefix="lcd",
        )
        wr = self.add("displayModule_write", inputs={"TEXT": self.txt(text)}, prefix="lcd")
        return self.link(cur, wr)

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

    def binh_thuong(self) -> str:
        a = self.set_xe(False, False, True)
        b = self.set_nguoi(True, False, False)
        c = self.servo("90")
        d = self.pin_out(BUZZER, False)
        e = self.pin_out(LED_BAO, False)
        f = self.lcd_text("1", "1", "Xe: XANH")
        g = self.lcd_text("2", "1", "HS: DUNG")
        self.link(a, b, c, d, e, f, g)
        return a

    def sang_duong(self) -> str:
        a = self.set_xe(True, False, False)
        b = self.set_nguoi(False, False, True)
        c = self.servo("0")
        d = self.pin_out(BUZZER, True)
        e = self.pin_out(LED_BAO, True)
        f = self.lcd_text("1", "1", "HS SANG!")
        g = self.lcd_text("2", "1", "Canh bao ON")
        h = self.wait("5")
        self.link(a, b, c, d, e, f, g, h)
        return a

    def condition_hs_an_toan(self) -> str:
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
        and_id = self.add("operator_and", prefix="and")
        self.blocks[and_id]["inputs"] = {
            "OPERAND1": [2, eq],
            "OPERAND2": [2, gt],
        }
        return and_id

    def build(self) -> dict[str, dict]:
        hat = self.add("arduinoUno_arduinoUnoStartUp", top=True, prefix="hat")
        forever = self.add("control_forever", prefix="f")
        self.link(hat, forever)

        # Khoi tao
        t1 = self.lcd_init()
        t2 = self.lcd_text("1", "1", "Smart Crossing")
        t3 = self.lcd_text("2", "1", "Khoi dong...")
        self.link(t1, t2, t3)

        normal = self.binh_thuong()
        self.link(t3, normal)

        if_id = self.add("control_if", prefix="if")
        cond = self.condition_hs_an_toan()
        self.blocks[if_id]["inputs"]["CONDITION"] = [2, cond]
        cross = self.sang_duong()
        self.blocks[if_id]["inputs"]["SUBSTACK"] = [2, cross]
        self.blocks[cross]["parent"] = if_id
        self.link(normal, if_id)

        # Ket thuc chu ky sang duong
        last = [k for k, v in self.blocks.items() if v.get("opcode") == "control_wait"][-1]
        tail = self.link(
            self.pin_out(BUZZER, False),
            self.pin_out(LED_BAO, False),
            self.servo("90"),
            self.wait("1"),
        )
        self.link(last, tail)

        self.blocks[forever]["inputs"] = {"SUBSTACK": [2, t1]}
        self.blocks[t1]["parent"] = forever
        return self.blocks


def main() -> None:
    if not TEMPLATE.exists():
        raise SystemExit(f"Missing template: {TEMPLATE}")

    project = json.loads(zipfile.ZipFile(TEMPLATE).read("project.json"))
    project["extensions"] = ["arduinoUno", "sensors", "displayModule", "actuators"]
    project["meta"]["agent"] = "smart-school-crossing-generator"

    for target in project["targets"]:
        if target.get("isStage"):
            target["blocks"] = {}
        else:
            target["name"] = "Smart Crossing"
            target["blocks"] = B().build()

    data = json.dumps(project, ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(TEMPLATE, "r") as zin, zipfile.ZipFile(OUTPUT, "w") as zout:
        for item in zin.infolist():
            zout.writestr(item, data if item.filename == "project.json" else zin.read(item.filename))

    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()
