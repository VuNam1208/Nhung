#!/usr/bin/env python3
"""Generate attendance SB3 matching the Thu Trang sample project style."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


OUTPUT = Path(__file__).with_name("cham-cong-teachable-machine.sb3")
MODEL_URL = "Paste your Teachable Machine model URL here!"
MEMBERS = ("Trang", "Thỏ", "rắn")
ABSENT_LABELS = ("Thu Trang", "Thỏ", "rắn")
ATTENDANCE_SECONDS = 10
LIST_ID = "attendance_list_id"
LIST_NAME = "Danh sách chấm công"
BROADCAST_START = "Thời gian chấm công"
BROADCAST_END = "Hết giờ"


class ProjectBuilder:
    def __init__(self) -> None:
        self.blocks: dict[str, dict] = {}
        self.counter = 0

    def identifier(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}_{self.counter:03d}"

    def block(
        self,
        opcode: str,
        *,
        parent: str | None = None,
        inputs: dict | None = None,
        fields: dict | None = None,
        shadow: bool = False,
        top_level: bool = False,
        x: int = 0,
        y: int = 0,
        prefix: str = "block",
    ) -> str:
        block_id = self.identifier(prefix)
        value = {
            "opcode": opcode,
            "next": None,
            "parent": parent,
            "inputs": inputs or {},
            "fields": fields or {},
            "shadow": shadow,
            "topLevel": top_level,
        }
        if top_level:
            value["x"] = x
            value["y"] = y
        self.blocks[block_id] = value
        return block_id

    def text_input(self, value: str) -> list:
        return [1, [10, value]]

    def number_input(self, value: int | float) -> list:
        return [1, [4, str(value)]]

    def link(self, *block_ids: str) -> None:
        for current, following in zip(block_ids, block_ids[1:]):
            self.blocks[current]["next"] = following
            self.blocks[following]["parent"] = current

    def say(self, message: str, seconds: int, parent: str) -> str:
        return self.block(
            "looks_sayforsecs",
            parent=parent,
            inputs={
                "MESSAGE": self.text_input(message),
                "SECS": self.number_input(seconds),
            },
            prefix="say",
        )

    def wait(self, seconds: float, parent: str, prefix: str = "wait") -> str:
        return self.block(
            "control_wait",
            parent=parent,
            inputs={"DURATION": self.number_input(seconds)},
            prefix=prefix,
        )

    def broadcast(self, message: str, parent: str) -> str:
        return self.block(
            "event_broadcast",
            parent=parent,
            fields={"BROADCAST_INPUT": [message, message]},
            prefix="broadcast",
        )

    def list_item_equals_zero(self, index: int, parent: str) -> str:
        equals_id = self.block("operator_equals", parent=parent, prefix="item_zero")
        item = self.block(
            "data_itemoflist",
            parent=equals_id,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix="item",
        )
        self.blocks[item]["inputs"] = {"INDEX": self.number_input(index)}
        self.blocks[equals_id]["inputs"] = {
            "OPERAND1": [2, item],
            "OPERAND2": self.number_input(0),
        }
        return equals_id

    def item_not_zero(self, index: int, parent: str) -> str:
        not_id = self.block("operator_not", parent=parent, prefix="not_zero")
        zero_eq = self.list_item_equals_zero(index, not_id)
        self.blocks[not_id]["inputs"] = {"OPERAND": [2, zero_eq]}
        return not_id

    def all_slots_filled(self, parent: str) -> str:
        first = self.item_not_zero(1, parent)
        current = first
        for index in range(2, len(MEMBERS) + 1):
            next_check = self.item_not_zero(index, parent)
            combined = self.block("operator_and", parent=parent, prefix="filled_and")
            self.blocks[combined]["inputs"] = {
                "OPERAND1": [2, current],
                "OPERAND2": [2, next_check],
            }
            self.blocks[current]["parent"] = combined
            current = combined
        return current

    def prediction_is(self, member: str, parent: str) -> str:
        return self.block(
            "teachableMachine_modelMatches",
            parent=parent,
            fields={"CLASS_NAME": [member, None]},
            prefix=f"pred_{member}",
        )

    def replace_list_item(self, index: int, value: str, parent: str) -> str:
        block_id = self.block(
            "data_replaceitemoflist",
            parent=parent,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix="replace",
        )
        self.blocks[block_id]["inputs"] = {
            "INDEX": self.number_input(index),
            "ITEM": self.text_input(value),
        }
        return block_id


def create_assets() -> tuple[tuple[str, bytes], tuple[str, bytes], tuple[str, bytes]]:
    stage_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">
<rect width="480" height="360" fill="#87ceeb"/>
<rect x="250" y="20" width="210" height="220" rx="10" fill="#fff" stroke="#333" stroke-width="2"/>
<text x="355" y="45" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">Danh sach cham cong</text>
</svg>"""
    avery_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="120" height="180">
<circle cx="60" cy="45" r="28" fill="#f2c094"/>
<rect x="30" y="75" width="60" height="80" rx="12" fill="#8d6e63"/>
<rect x="18" y="85" width="18" height="55" rx="8" fill="#f2c094"/>
<rect x="84" y="85" width="18" height="55" rx="8" fill="#f2c094"/>
</svg>"""
    counter_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80">
<rect width="120" height="80" rx="8" fill="#1b5e20"/>
<text x="60" y="52" text-anchor="middle" font-family="Arial" font-size="36" fill="#69f0ae">09</text>
</svg>"""
    return (
        (hashlib.md5(stage_svg).hexdigest() + ".svg", stage_svg),
        (hashlib.md5(avery_svg).hexdigest() + ".svg", avery_svg),
        (hashlib.md5(counter_svg).hexdigest() + ".svg", counter_svg),
    )


def costume(asset: tuple[str, bytes], name: str, cx: int, cy: int) -> dict:
    filename, _ = asset
    return {
        "assetId": filename.removesuffix(".svg"),
        "name": name,
        "bitmapResolution": 1,
        "md5ext": filename,
        "dataFormat": "svg",
        "rotationCenterX": cx,
        "rotationCenterY": cy,
    }


def build_detection_for_member(
    builder: ProjectBuilder, member: str, index: int, parent: str
) -> str:
    detect_if = builder.block("control_if", parent=parent, prefix=f"if_{member}")
    prediction = builder.prediction_is(member, detect_if)
    slot_if = builder.block("control_if", parent=detect_if, prefix=f"slot_{member}")
    slot_empty = builder.list_item_equals_zero(index, slot_if)
    hello = builder.say(f"Xin chao {member}!", 2, slot_if)
    replace_item = builder.replace_list_item(index, member, hello)
    builder.link(hello, replace_item)
    builder.blocks[slot_if]["inputs"] = {
        "CONDITION": [2, slot_empty],
        "SUBSTACK": [2, hello],
    }
    builder.blocks[detect_if]["inputs"] = {
        "CONDITION": [2, prediction],
        "SUBSTACK": [2, slot_if],
    }
    return detect_if


def build_avery_blocks() -> tuple[dict, dict]:
    builder = ProjectBuilder()

    # Khoi 1: khi bam co xanh
    flag = builder.block(
        "event_whenflagclicked", top_level=True, x=20, y=20, prefix="flag"
    )
    use_model = builder.block(
        "teachableMachine_useModelBlock",
        parent=flag,
        inputs={"MODEL_URL": builder.text_input(MODEL_URL)},
        prefix="use_model",
    )
    transparency = builder.block(
        "teachableMachine_setVideoTransparency",
        parent=flag,
        inputs={"TRANSPARENCY": builder.number_input(20)},
        prefix="transparency",
    )
    builder.link(flag, use_model, transparency)

    # Khoi 2: phim a bat dau cham cong
    key_a = builder.block(
        "event_whenkeypressed",
        fields={"KEY_OPTION": ["a", None]},
        top_level=True,
        x=20,
        y=180,
        prefix="key_a",
    )
    clear_list = builder.block(
        "data_deletealloflist",
        parent=key_a,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix="clear",
    )
    init_slots = []
    parent = clear_list
    for _ in MEMBERS:
        add_zero = builder.block(
            "data_addtolist",
            parent=parent,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            inputs={"ITEM": builder.number_input(0)},
            prefix="add_zero",
        )
        init_slots.append(add_zero)
        parent = add_zero
    intro = builder.say("Bảng chấm công", 3, parent)
    video_on = builder.block("teachableMachine_videoToggle", parent=intro, prefix="video_on")
    video_menu = builder.block(
        "teachableMachine_menu_VIDEO_STATE",
        parent=video_on,
        fields={"VIDEO_STATE": ["on", None]},
        shadow=True,
        prefix="video_menu",
    )
    builder.blocks[video_on]["inputs"] = {"VIDEO_STATE": [1, video_menu]}
    start_timer = builder.broadcast(BROADCAST_START, video_on)
    builder.link(key_a, clear_list, *init_slots, intro, video_on, start_timer)

    # Khoi 3: nhan dien lien tuc trong thoi gian cham cong
    receive_start = builder.block(
        "event_whenbroadcastreceived",
        fields={"BROADCAST_OPTION": [BROADCAST_START, BROADCAST_START]},
        top_level=True,
        x=420,
        y=20,
        prefix="recv_start",
    )
    repeat = builder.block("control_repeat_until", parent=receive_start, prefix="repeat")
    time_done = builder.block("operator_equals", parent=repeat, prefix="time_done")
    time_value = builder.block(
        "data_variable",
        parent=time_done,
        fields={"VARIABLE": ["time", "time_var"]},
        prefix="time_value",
    )
    builder.blocks[time_done]["inputs"] = {
        "OPERAND1": [2, time_value],
        "OPERAND2": builder.number_input(0),
    }
    detect_blocks = []
    for index, member in enumerate(MEMBERS, start=1):
        parent_for = detect_blocks[-1] if detect_blocks else repeat
        detect = build_detection_for_member(builder, member, index, parent_for)
        detect_blocks.append(detect)
    pause = builder.wait(0.2, detect_blocks[-1], prefix="pause")
    builder.link(*detect_blocks, pause)
    builder.blocks[repeat]["inputs"] = {
        "CONDITION": [2, time_done],
        "SUBSTACK": [2, detect_blocks[0]],
    }

    # Khoi 4: ket qua khi het gio
    receive_end = builder.block(
        "event_whenbroadcastreceived",
        fields={"BROADCAST_OPTION": [BROADCAST_END, BROADCAST_END]},
        top_level=True,
        x=420,
        y=360,
        prefix="recv_end",
    )
    full_if = builder.block("control_if_else", parent=receive_end, prefix="full_if")
    full_condition = builder.all_slots_filled(full_if)
    full_say = builder.say("Mọi người đã đến đầy đủ", 2, full_if)
    missing_checks = []
    parent_missing = full_if
    for index, label in enumerate(ABSENT_LABELS, start=1):
        check = builder.block("control_if", parent=parent_missing, prefix=f"miss_{index}")
        still_empty = builder.list_item_equals_zero(index, check)
        absent_say = builder.say(f"Vắng {label}", 2, check)
        builder.blocks[check]["inputs"] = {
            "CONDITION": [2, still_empty],
            "SUBSTACK": [2, absent_say],
        }
        missing_checks.append(check)
        parent_missing = check
    builder.link(*missing_checks)
    builder.blocks[full_if]["inputs"] = {
        "CONDITION": [2, full_condition],
        "SUBSTACK": [2, full_say],
        "SUBSTACK2": [2, missing_checks[0]],
    }
    video_off = builder.block("teachableMachine_videoToggle", parent=parent_missing, prefix="video_off")
    off_menu = builder.block(
        "teachableMachine_menu_VIDEO_STATE",
        parent=video_off,
        fields={"VIDEO_STATE": ["off", None]},
        shadow=True,
        prefix="off_menu",
    )
    builder.blocks[video_off]["inputs"] = {"VIDEO_STATE": [1, off_menu]}
    builder.link(receive_end, full_if, video_off)

    comments = {
        "help": {
            "blockId": use_model,
            "x": 260,
            "y": 40,
            "width": 280,
            "height": 120,
            "minimized": False,
            "text": (
                "Giong bai mau: dan link model, bam phim a de cham cong. "
                "Class phai la: Trang, Tho, ran."
            ),
        }
    }
    return builder.blocks, comments


def build_counter_blocks() -> dict:
    builder = ProjectBuilder()
    receive = builder.block(
        "event_whenbroadcastreceived",
        fields={"BROADCAST_OPTION": [BROADCAST_START, BROADCAST_START]},
        top_level=True,
        x=40,
        y=40,
        prefix="counter_recv",
    )
    set_time = builder.block(
        "data_setvariableto",
        parent=receive,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": builder.number_input(ATTENDANCE_SECONDS)},
        prefix="set_time",
    )
    repeat = builder.block("control_repeat", parent=set_time, prefix="repeat")
    builder.blocks[repeat]["inputs"] = {"TIMES": builder.number_input(ATTENDANCE_SECONDS)}
    wait = builder.wait(1, repeat, prefix="tick_wait")
    decrement = builder.block(
        "data_changevariableby",
        parent=wait,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": builder.number_input(-1)},
        prefix="tick",
    )
    builder.link(wait, decrement)
    builder.blocks[repeat]["inputs"]["SUBSTACK"] = [2, wait]
    end_broadcast = builder.broadcast(BROADCAST_END, repeat)
    builder.link(receive, set_time, repeat, end_broadcast)
    return builder.blocks


def build_project() -> dict:
    stage_assets = create_assets()
    stage_file, avery_file, counter_file = stage_assets
    avery_blocks, comments = build_avery_blocks()
    counter_blocks = build_counter_blocks()

    initial_list = [0, 0, 0]
    return {
        "targets": [
            {
                "isStage": True,
                "name": "Stage",
                "variables": {
                    "time_var": ["time", ATTENDANCE_SECONDS],
                },
                "lists": {
                    LIST_ID: [LIST_NAME, initial_list],
                },
                "broadcasts": {
                    BROADCAST_START: BROADCAST_START,
                    BROADCAST_END: BROADCAST_END,
                },
                "blocks": {},
                "comments": {},
                "currentCostume": 0,
                "costumes": [
                    costume(stage_file, "San khau", 240, 180),
                ],
                "sounds": [],
                "volume": 100,
                "layerOrder": 0,
                "tempo": 60,
                "videoTransparency": 20,
                "videoState": "off",
                "textToSpeechLanguage": None,
            },
            {
                "isStage": False,
                "name": "Avery",
                "variables": {},
                "lists": {},
                "broadcasts": {},
                "blocks": avery_blocks,
                "comments": comments,
                "currentCostume": 0,
                "costumes": [costume(avery_file, "Avery", 60, 90)],
                "sounds": [],
                "volume": 100,
                "layerOrder": 2,
                "visible": True,
                "x": -150,
                "y": -20,
                "size": 80,
                "direction": 90,
                "draggable": False,
                "rotationStyle": "all around",
            },
            {
                "isStage": False,
                "name": "Bang dem",
                "variables": {},
                "lists": {},
                "broadcasts": {},
                "blocks": counter_blocks,
                "comments": {},
                "currentCostume": 0,
                "costumes": [costume(counter_file, "Dem", 60, 40)],
                "sounds": [],
                "volume": 100,
                "layerOrder": 1,
                "visible": True,
                "x": 150,
                "y": 100,
                "size": 100,
                "direction": 90,
                "draggable": False,
                "rotationStyle": "all around",
            },
        ],
        "monitors": [
            {
                "id": LIST_ID,
                "mode": "list",
                "opcode": "data_listcontents",
                "params": {"LIST": LIST_NAME},
                "spriteName": None,
                "value": initial_list,
                "width": 0,
                "height": 0,
                "x": 255,
                "y": 15,
                "visible": True,
            },
            {
                "id": "time_var",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "time"},
                "spriteName": None,
                "value": ATTENDANCE_SECONDS,
                "width": 0,
                "height": 0,
                "x": 150,
                "y": 65,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": ATTENDANCE_SECONDS,
                "isDiscrete": True,
            },
            {
                "id": "prediction_monitor",
                "mode": "default",
                "opcode": "teachableMachine_modelPrediction",
                "params": {},
                "spriteName": "Avery",
                "value": "",
                "width": 0,
                "height": 0,
                "x": 12,
                "y": 12,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 100,
                "isDiscrete": True,
            },
        ],
        "extensions": ["teachableMachine"],
        "meta": {
            "semver": "3.0.0",
            "vm": "11.1.0",
            "agent": "Cursor - Thu Trang attendance style",
        },
    }


def validate_project(project: dict) -> None:
    avery = next(t for t in project["targets"] if t["name"] == "Avery")
    opcodes = {block["opcode"] for block in avery["blocks"].values()}
    required = {
        "event_whenkeypressed",
        "teachableMachine_useModelBlock",
        "control_repeat_until",
        "teachableMachine_modelMatches",
        "event_whenbroadcastreceived",
    }
    missing = required - opcodes
    if missing:
        raise ValueError(f"Missing opcodes: {missing}")


def main() -> None:
    project = build_project()
    validate_project(project)
    stage_file, avery_file, counter_file = create_assets()
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "project.json",
            json.dumps(project, ensure_ascii=False, separators=(",", ":")),
        )
        archive.writestr(*stage_file)
        archive.writestr(*avery_file)
        archive.writestr(*counter_file)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
