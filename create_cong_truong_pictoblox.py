#!/usr/bin/env python3
"""PictoBlox Stage Mode: Cong truong an toan + Camera AI + Arduino."""

from __future__ import annotations

import json
import secrets
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


def scratch_id() -> str:
    return secrets.token_hex(10)


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

    def connect(self, a: str, b: str) -> None:
        self.blocks[a]["next"] = b
        self.blocks[b]["parent"] = a

    def chain(self, *ids: str) -> tuple[str, str]:
        for a, c in zip(ids, ids[1:]):
            self.connect(a, c)
        return ids[0], ids[-1]

    def attach(self, parent: str, name: str, child: str, kind: int = 2) -> None:
        self.blocks[parent]["inputs"][name] = [kind, child]
        self.blocks[child]["parent"] = parent

    def num(self, v: str | int | float) -> list:
        return [1, [4, str(v)]]

    def txt(self, v: str) -> list:
        return [1, [10, v]]

    def set_var(self, name: str, vid: str, value: int, parent: str | None = None) -> str:
        return self.add(
            "data_setvariableto",
            parent=parent,
            fields={"VARIABLE": [name, vid]},
            inputs={"VALUE": self.num(value)},
            prefix="sv",
        )

    def wait(self, sec: str, parent: str | None = None) -> str:
        return self.add(
            "control_wait",
            parent=parent,
            inputs={"DURATION": self.num(sec)},
            prefix="w",
        )

    def pin_out(self, pin: str, high: bool, parent: str | None = None) -> str:
        return self.add(
            "arduinoUno_digitalWrite",
            parent=parent,
            fields={"PIN": [pin, None], "MODE": ["true" if high else "false", None]},
            prefix="po",
        )

    def servo(self, angle: str, parent: str | None = None) -> str:
        return self.add(
            "actuators_setServoOnPinToAngle",
            parent=parent,
            fields={"PIN": [SERVO, None], "ANGLE": [angle, None]},
            prefix="svo",
        )

    def lcd_init(self, parent: str | None = None) -> tuple[str, str]:
        a = self.add(
            "displayModule_initialiseI2CDisplay",
            parent=parent,
            inputs={"I2C_ADD": self.num(LCD_ADDR)},
            prefix="lcd",
        )
        b = self.add("displayModule_clearDisplay", prefix="lcd")
        return self.chain(a, b)

    def lcd_text(self, row: str, col: str, text: str, parent: str | None = None) -> tuple[str, str]:
        a = self.add(
            "displayModule_setCursor",
            parent=parent,
            fields={"ROW": [row, None], "COLUMN": [col, None]},
            prefix="lcd",
        )
        b = self.add("displayModule_write", inputs={"TEXT": self.txt(text)}, prefix="lcd")
        return self.chain(a, b)

    def set_xe(self, do: bool, vang: bool, xanh: bool, parent: str | None = None) -> tuple[str, str]:
        a = self.pin_out(XE["do"], do, parent)
        b = self.pin_out(XE["vang"], vang)
        c = self.pin_out(XE["xanh"], xanh)
        return self.chain(a, b, c)

    def set_nguoi(self, do: bool, vang: bool, xanh: bool, parent: str | None = None) -> tuple[str, str]:
        a = self.pin_out(NGUOI["do"], do, parent)
        b = self.pin_out(NGUOI["vang"], vang)
        c = self.pin_out(NGUOI["xanh"], xanh)
        return self.chain(a, b, c)

    def join(self, tail: str, head: str) -> str:
        self.connect(tail, head)
        return head

    def var_is_one(self, parent: str) -> str:
        eq = self.add("operator_equals", parent=parent, prefix="eq")
        ref = self.add(
            "data_variable",
            fields={"VARIABLE": [VAR_AI[0], VAR_AI[1]]},
            prefix="vr",
        )
        self.attach(eq, "OPERAND1", ref)
        self.blocks[eq]["inputs"]["OPERAND2"] = self.num(1)
        return eq

    def sensor_ok(self, parent: str) -> str:
        ir = self.add(
            "arduinoUno_digitalRead",
            parent=parent,
            fields={"PIN": [IR_PIN, None]},
            prefix="ir",
        )
        eq = self.add("operator_equals", parent=parent, prefix="eq")
        self.attach(eq, "OPERAND1", ir)
        self.blocks[eq]["inputs"]["OPERAND2"] = [1, [10, "false"]]

        us = self.add(
            "sensors_readUltrasonic",
            parent=parent,
            fields={"TRIG_PIN": [TRIG, None], "ECHO_PIN": [ECHO, None]},
            prefix="us",
        )
        gt = self.add("operator_gt", parent=parent, prefix="gt")
        self.attach(gt, "OPERAND1", us)
        self.blocks[gt]["inputs"]["OPERAND2"] = self.num(30)

        both = self.add("operator_and", parent=parent, prefix="and")
        self.attach(both, "OPERAND1", eq)
        self.attach(both, "OPERAND2", gt)
        return both

    def full_condition(self, parent: str) -> str:
        ai = self.var_is_one(parent)
        sen = self.sensor_ok(parent)
        both = self.add("operator_and", parent=parent, prefix="and")
        self.attach(both, "OPERAND1", ai)
        self.attach(both, "OPERAND2", sen)
        return both

    def binh_thuong(self, parent: str | None = None) -> tuple[str, str]:
        xe0, xe1 = self.set_xe(False, False, True, parent)
        ng0, ng1 = self.set_nguoi(True, False, False)
        self.join(xe1, ng0)
        s = self.servo("90")
        self.join(ng1, s)
        bz = self.pin_out(BUZZER, False)
        self.join(s, bz)
        led = self.pin_out(LED_BAO, False)
        self.join(bz, led)
        l1_0, l1_1 = self.lcd_text("1", "1", "Xe: XANH")
        self.join(led, l1_0)
        l2_0, l2_1 = self.lcd_text("2", "1", "HS: DUNG")
        self.join(l1_1, l2_0)
        return xe0, l2_1

    def sang_duong(self, parent: str | None = None) -> tuple[str, str]:
        xe0, xe1 = self.set_xe(True, False, False, parent)
        ng0, ng1 = self.set_nguoi(False, False, True)
        self.join(xe1, ng0)
        s = self.servo("0")
        self.join(ng1, s)
        bz = self.pin_out(BUZZER, True)
        self.join(s, bz)
        led = self.pin_out(LED_BAO, True)
        self.join(bz, led)
        l1_0, l1_1 = self.lcd_text("1", "1", "HS SANG!")
        self.join(led, l1_0)
        l2_0, l2_1 = self.lcd_text("2", "1", "AI OK")
        self.join(l1_1, l2_0)
        w = self.wait("5")
        self.join(l2_1, w)
        bz2 = self.pin_out(BUZZER, False)
        self.join(w, bz2)
        led2 = self.pin_out(LED_BAO, False)
        self.join(bz2, led2)
        s2 = self.servo("90")
        self.join(led2, s2)
        w2 = self.wait("1")
        self.join(s2, w2)
        return xe0, w2


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
    b.blocks[vonm]["parent"] = von
    trans = b.add(
        "teachableMachine_setVideoTransparency",
        inputs={"TRANSPARENCY": b.num(20)},
        prefix="tm",
    )
    wait = b.add("control_wait", inputs={"DURATION": b.num(3)}, prefix="w")
    b.chain(flag, use, von, trans, wait)

    forever = b.add("control_forever", prefix="fr")
    b.connect(wait, forever)

    if_yes = b.add("control_if", prefix="if")
    pred_yes = b.add(
        "teachableMachine_modelMatches",
        fields={"CLASS_NAME": [CLASS_HS, None]},
        prefix="tm",
    )
    set1 = b.set_var(VAR_AI[0], VAR_AI[1], 1)
    b.attach(if_yes, "CONDITION", pred_yes)
    b.blocks[if_yes]["inputs"]["SUBSTACK"] = [2, set1]
    b.blocks[set1]["parent"] = if_yes

    if_no = b.add("control_if", prefix="if")
    pred_no = b.add(
        "teachableMachine_modelMatches",
        fields={"CLASS_NAME": [CLASS_HS, None]},
        prefix="tm",
    )
    not_pred = b.add("operator_not", prefix="nt")
    b.attach(not_pred, "OPERAND", pred_no)
    set0 = b.set_var(VAR_AI[0], VAR_AI[1], 0)
    b.attach(if_no, "CONDITION", not_pred)
    b.blocks[if_no]["inputs"]["SUBSTACK"] = [2, set0]
    b.blocks[set0]["parent"] = if_no

    delay = b.wait("0.2")
    b.chain(if_yes, if_no, delay)
    b.blocks[forever]["inputs"] = {"SUBSTACK": [2, if_yes]}
    b.blocks[if_yes]["parent"] = forever

    return b.blocks


def build_arduino_sprite() -> dict:
    b = B()
    flag = b.add("event_whenflagclicked", top=True, prefix="f")
    lcd0, lcd1 = b.lcd_init()
    t1_0, t1_1 = b.lcd_text("1", "1", "Cong Truong AT")
    b.join(lcd1, t1_0)
    t2_0, t2_1 = b.lcd_text("2", "1", "Smart Crossing")
    b.join(t1_1, t2_0)
    b.chain(flag, lcd0)

    forever = b.add("control_forever", prefix="fr")
    b.connect(t2_1, forever)

    normal0, normal1 = b.binh_thuong()
    if_id = b.add("control_if", prefix="if")
    cond = b.full_condition(if_id)
    b.attach(if_id, "CONDITION", cond)
    cross0, cross1 = b.sang_duong()
    b.blocks[if_id]["inputs"]["SUBSTACK"] = [2, cross0]
    b.blocks[cross0]["parent"] = if_id
    pause = b.wait("0.3")
    b.join(normal1, if_id)
    b.join(if_id, pause)
    b.blocks[forever]["inputs"] = {"SUBSTACK": [2, normal0]}
    b.blocks[normal0]["parent"] = forever

    return b.blocks


def sprite_from_template(tpl: dict, name: str, blocks: dict, layer: int) -> dict:
    s = json.loads(json.dumps(tpl))
    s["name"] = name
    s["blocks"] = blocks
    s["id"] = scratch_id()
    s["layerOrder"] = layer
    return s


def validate_blocks(blocks: dict, label: str) -> None:
    orphans = []
    for bid, blk in blocks.items():
        if blk.get("topLevel") or blk.get("shadow"):
            continue
        if blk.get("parent") is not None:
            continue
        referenced = False
        for ob in blocks.values():
            for inp in ob.get("inputs", {}).values():
                if isinstance(inp, list) and len(inp) >= 2 and inp[1] == bid:
                    referenced = True
        if not referenced:
            orphans.append((bid, blk["opcode"]))
    if orphans:
        raise SystemExit(f"{label}: orphan blocks {orphans}")


def main() -> None:
    if not STAGE_TEMPLATE.exists():
        raise SystemExit(f"Missing template: {STAGE_TEMPLATE}")

    with zipfile.ZipFile(STAGE_TEMPLATE, "r") as zin:
        base = json.loads(zin.read("project.json"))

    cam_blocks = build_camera_ai_sprite()
    ard_blocks = build_arduino_sprite()
    validate_blocks(cam_blocks, "Camera AI")
    validate_blocks(ard_blocks, "Arduino Gate")

    stage = base["targets"][0]
    tpl = base["targets"][1]
    stage["variables"] = {VAR_AI[1]: [VAR_AI[0], 0]}
    stage["blocks"] = {}
    stage["id"] = scratch_id()

    cam = sprite_from_template(tpl, "Camera AI", cam_blocks, 1)
    ard = sprite_from_template(tpl, "Arduino Gate", ard_blocks, 2)
    cam["x"] = -120
    ard["x"] = 120

    project = base
    project["extensions"] = [
        "arduinoUno",
        "sensors",
        "displayModule",
        "actuators",
        "teachableMachine",
    ]
    project["meta"]["agent"] = "cong-truong-an-toan-ai-v2"
    project["targets"] = [stage, cam, ard]

    data = json.dumps(project, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with zipfile.ZipFile(STAGE_TEMPLATE, "r") as zin, zipfile.ZipFile(
        OUTPUT, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            zout.writestr(
                item, data if item.filename == "project.json" else zin.read(item.filename)
            )

    print(f"Created: {OUTPUT}")
    print(f"  Camera AI blocks: {len(cam_blocks)}")
    print(f"  Arduino Gate blocks: {len(ard_blocks)}")


if __name__ == "__main__":
    main()
