#!/usr/bin/env python3
"""Generate a RAISE Playground .sb3 attendance project."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


OUTPUT = Path(__file__).with_name("cham-cong-teachable-machine.sb3")
MODEL_URL = "Paste your Teachable Machine model URL here!"
MEMBERS = ("An", "Binh", "Chi")
SECONDS_PER_PERSON = 15
MODEL_LOAD_SECONDS = 5
ATTENDANCE_LIST_ID = "attendance_list_id"
ATTENDANCE_LIST_NAME = "danh_sach_cham_cong"
MEMBER_STATUS = {
    "An": ("An: chua den", "An: da den", 1),
    "Binh": ("Binh: chua den", "Binh: da den", 2),
    "Chi": ("Chi: chua den", "Chi: da den", 3),
}
MEMBER_VARIABLES = {
    "An": ("An_den", "an_var"),
    "Binh": ("Binh_den", "binh_var"),
    "Chi": ("Chi_den", "chi_var"),
}


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
        x: int | None = None,
        y: int | None = None,
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
            value["x"] = x or 0
            value["y"] = y or 0
        self.blocks[block_id] = value
        return block_id

    def text_input(self, value: str) -> list:
        return [1, [10, value]]

    def number_input(self, value: int | float) -> list:
        return [1, [4, str(value)]]

    def variable_reporter(self, name: str, variable_id: str, parent: str) -> str:
        return self.block(
            "data_variable",
            parent=parent,
            fields={"VARIABLE": [name, variable_id]},
            prefix=f"read_{name}",
        )

    def equals_variable(
        self, name: str, variable_id: str, expected: int, parent: str
    ) -> str:
        equals_id = self.block("operator_equals", parent=parent, prefix="equals")
        variable_block = self.variable_reporter(name, variable_id, equals_id)
        self.blocks[equals_id]["inputs"] = {
            "OPERAND1": [2, variable_block],
            "OPERAND2": self.number_input(expected),
        }
        return equals_id

    def set_variable(
        self, name: str, variable_id: str, value: str | int, parent: str
    ) -> str:
        value_input = (
            self.number_input(value) if isinstance(value, int) else self.text_input(value)
        )
        return self.block(
            "data_setvariableto",
            parent=parent,
            inputs={"VALUE": value_input},
            fields={"VARIABLE": [name, variable_id]},
            prefix=f"set_{name}",
        )

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

    def delete_all_list(self, list_name: str, list_id: str, parent: str) -> str:
        return self.block(
            "data_deletealloflist",
            parent=parent,
            fields={"LIST": [list_name, list_id]},
            prefix="clear_list",
        )

    def add_to_list(
        self, item: str, list_name: str, list_id: str, parent: str
    ) -> str:
        return self.block(
            "data_addtolist",
            parent=parent,
            fields={"LIST": [list_name, list_id]},
            inputs={"ITEM": self.text_input(item)},
            prefix="add_list",
        )

    def replace_list_item(
        self, index: int, item: str, list_name: str, list_id: str, parent: str
    ) -> str:
        block_id = self.block(
            "data_replaceitemoflist",
            parent=parent,
            fields={"LIST": [list_name, list_id]},
            prefix="replace_list",
        )
        self.blocks[block_id]["inputs"] = {
            "INDEX": self.number_input(index),
            "ITEM": self.text_input(item),
        }
        return block_id

    def prediction_is(self, member: str, parent: str) -> str:
        return self.block(
            "teachableMachine_modelMatches",
            parent=parent,
            fields={"CLASS_NAME": [member, None]},
            prefix=f"pred_{member}",
        )

    def prediction_equals(self, member: str, parent: str) -> str:
        equals_id = self.block("operator_equals", parent=parent, prefix="pred_eq")
        prediction = self.block(
            "teachableMachine_modelPrediction",
            parent=equals_id,
            prefix="pred_value",
        )
        self.blocks[equals_id]["inputs"] = {
            "OPERAND1": [2, prediction],
            "OPERAND2": self.text_input(member),
        }
        return equals_id

    def or_condition(self, left_id: str, right_id: str, parent: str) -> str:
        or_id = self.block("operator_or", parent=parent, prefix="or")
        self.blocks[or_id]["inputs"] = {
            "OPERAND1": [2, left_id],
            "OPERAND2": [2, right_id],
        }
        return or_id

    def wait_seconds(self, seconds: float, parent: str, prefix: str = "wait") -> str:
        return self.block(
            "control_wait",
            parent=parent,
            inputs={"DURATION": self.number_input(seconds)},
            prefix=prefix,
        )

    def link(self, *block_ids: str) -> None:
        for current, following in zip(block_ids, block_ids[1:]):
            self.blocks[current]["next"] = following
            self.blocks[following]["parent"] = current


def create_assets() -> tuple[tuple[str, bytes], tuple[str, bytes]]:
    stage_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">
<rect width="480" height="360" fill="#f4f7fb"/>
<rect x="20" y="20" width="440" height="320" rx="18" fill="#ffffff" stroke="#4c97ff" stroke-width="4"/>
<text x="240" y="62" text-anchor="middle" font-family="Arial" font-size="25" font-weight="bold" fill="#24508f">BANG CHAM CONG AI</text>
<rect x="292" y="24" width="168" height="210" rx="12" fill="#ffffff" stroke="#24508f" stroke-width="3"/>
<text x="376" y="48" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#24508f">DANH SACH</text>
<text x="240" y="320" text-anchor="middle" font-family="Arial" font-size="15" fill="#555">Luot cham cong: tung nguoi nhin camera 15 giay</text>
</svg>"""
    sprite_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="190" height="190">
<circle cx="95" cy="95" r="86" fill="#4c97ff"/>
<circle cx="95" cy="68" r="32" fill="#ffffff"/>
<path d="M35 154c8-38 31-57 60-57s52 19 60 57" fill="#ffffff"/>
<path d="M55 150l24 20 54-62" fill="none" stroke="#59c059" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
    stage_name = hashlib.md5(stage_svg).hexdigest() + ".svg"
    sprite_name = hashlib.md5(sprite_svg).hexdigest() + ".svg"
    return (stage_name, stage_svg), (sprite_name, sprite_svg)


def build_mark_member(builder: ProjectBuilder, member: str, parent: str) -> str:
    variable_name, variable_id = MEMBER_VARIABLES[member]
    detect_if = builder.block("control_if", parent=parent, prefix=f"detect_{member}")
    detected = builder.or_condition(
        builder.prediction_is(member, detect_if),
        builder.prediction_equals(member, detect_if),
        detect_if,
    )
    confirm_if = builder.block("control_if", parent=detect_if, prefix=f"confirm_{member}")
    is_new = builder.equals_variable(variable_name, variable_id, 0, confirm_if)
    mark_present = builder.set_variable(variable_name, variable_id, 1, confirm_if)
    update_list = builder.replace_list_item(
        MEMBER_STATUS[member][2],
        MEMBER_STATUS[member][1],
        ATTENDANCE_LIST_NAME,
        ATTENDANCE_LIST_ID,
        mark_present,
    )
    success = builder.say(f"{member} da cham cong thanh cong!", 2, update_list)
    builder.link(mark_present, update_list, success)
    builder.blocks[confirm_if]["inputs"] = {
        "CONDITION": [2, is_new],
        "SUBSTACK": [2, mark_present],
    }
    builder.blocks[detect_if]["inputs"] = {
        "CONDITION": [2, detected],
        "SUBSTACK": [2, confirm_if],
    }
    return detect_if


def build_member_turn(builder: ProjectBuilder, member: str, parent: str) -> tuple[str, str]:
    variable_name, variable_id = MEMBER_VARIABLES[member]
    set_timer = builder.set_variable(
        "person_time", "person_time_var", SECONDS_PER_PERSON, parent
    )
    set_current = builder.set_variable(
        "nguoi_dang_cho", "current_var", member, set_timer
    )
    prompt = builder.say(
        f"Luot cham cong: {member} - hay nhin thang vao camera!", 3, set_current
    )
    repeat = builder.block("control_repeat_until", parent=prompt, prefix=f"wait_{member}")
    is_marked = builder.equals_variable(variable_name, variable_id, 1, repeat)
    timer_done = builder.equals_variable("person_time", "person_time_var", 0, repeat)
    stop_condition = builder.or_condition(is_marked, timer_done, repeat)
    detect = build_mark_member(builder, member, repeat)
    wait = builder.wait_seconds(1, detect, prefix=f"pause_{member}")
    decrement = builder.block(
        "data_changevariableby",
        parent=wait,
        inputs={"VALUE": builder.number_input(-1)},
        fields={"VARIABLE": ["person_time", "person_time_var"]},
        prefix=f"tick_{member}",
    )
    builder.link(detect, wait, decrement)
    builder.blocks[repeat]["inputs"] = {
        "CONDITION": [2, stop_condition],
        "SUBSTACK": [2, detect],
    }
    missed_if = builder.block("control_if", parent=repeat, prefix=f"missed_{member}")
    still_missing = builder.equals_variable(variable_name, variable_id, 0, missed_if)
    missed_say = builder.say(
        f"Khong nhan dien duoc {member}. Hay thu lai hoac kiem tra model.", 2, missed_if
    )
    builder.blocks[missed_if]["inputs"] = {
        "CONDITION": [2, still_missing],
        "SUBSTACK": [2, missed_say],
    }
    builder.link(set_timer, set_current, prompt, repeat, missed_if)
    return set_timer, missed_if


def build_final_report(builder: ProjectBuilder, parent: str) -> str:
    final_if = builder.block("control_if_else", parent=parent, prefix="final_check")
    eq_an = builder.equals_variable("An_den", "an_var", 1, final_if)
    eq_binh = builder.equals_variable("Binh_den", "binh_var", 1, final_if)
    eq_chi = builder.equals_variable("Chi_den", "chi_var", 1, final_if)
    and_left = builder.block(
        "operator_and",
        parent=final_if,
        inputs={"OPERAND1": [2, eq_an], "OPERAND2": [2, eq_binh]},
        prefix="and",
    )
    and_all = builder.block(
        "operator_and",
        parent=final_if,
        inputs={"OPERAND1": [2, and_left], "OPERAND2": [2, eq_chi]},
        prefix="and_all",
    )
    builder.blocks[and_left]["parent"] = and_all
    full_message = builder.say("Moi nguoi da den day du!", 4, final_if)

    missing_start = builder.set_variable("result", "result_var", "Vang: ", final_if)
    missing_checks: list[str] = []
    previous = missing_start
    for member in MEMBERS:
        variable_name, variable_id = MEMBER_VARIABLES[member]
        check = builder.block("control_if", parent=previous, prefix=f"missing_{member}")
        condition = builder.equals_variable(variable_name, variable_id, 0, check)
        set_result = builder.block(
            "data_setvariableto",
            parent=check,
            fields={"VARIABLE": ["result", "result_var"]},
            prefix=f"append_{member}",
        )
        join = builder.block("operator_join", parent=set_result, prefix="join")
        result_reporter = builder.variable_reporter("result", "result_var", join)
        builder.blocks[join]["inputs"] = {
            "STRING1": [2, result_reporter],
            "STRING2": builder.text_input(member + " "),
        }
        builder.blocks[set_result]["inputs"] = {"VALUE": [2, join]}
        builder.blocks[check]["inputs"] = {
            "CONDITION": [2, condition],
            "SUBSTACK": [2, set_result],
        }
        missing_checks.append(check)
        previous = check
    missing_say = builder.block(
        "looks_sayforsecs",
        parent=previous,
        inputs={"SECS": builder.number_input(4)},
        prefix="say_missing",
    )
    result_reporter = builder.variable_reporter("result", "result_var", missing_say)
    builder.blocks[missing_say]["inputs"]["MESSAGE"] = [2, result_reporter]
    builder.link(missing_start, *missing_checks, missing_say)
    builder.blocks[final_if]["inputs"] = {
        "CONDITION": [2, and_all],
        "SUBSTACK": [2, full_message],
        "SUBSTACK2": [2, missing_start],
    }
    return final_if


def build_project() -> dict:
    builder = ProjectBuilder()
    variables = {
        "person_time_var": ["person_time", SECONDS_PER_PERSON],
        "current_var": ["nguoi_dang_cho", ""],
        "an_var": ["An_den", 0],
        "binh_var": ["Binh_den", 0],
        "chi_var": ["Chi_den", 0],
        "result_var": ["result", ""],
    }

    flag = builder.block(
        "event_whenflagclicked",
        top_level=True,
        x=35,
        y=35,
        prefix="green_flag",
    )
    initializers = [
        builder.set_variable("person_time", "person_time_var", SECONDS_PER_PERSON, flag),
        builder.set_variable("nguoi_dang_cho", "current_var", "", flag),
        builder.set_variable("An_den", "an_var", 0, flag),
        builder.set_variable("Binh_den", "binh_var", 0, flag),
        builder.set_variable("Chi_den", "chi_var", 0, flag),
        builder.set_variable("result", "result_var", "", flag),
    ]
    clear_list = builder.delete_all_list(
        ATTENDANCE_LIST_NAME, ATTENDANCE_LIST_ID, flag
    )
    list_initializers = [
        builder.add_to_list(
            MEMBER_STATUS[member][0],
            ATTENDANCE_LIST_NAME,
            ATTENDANCE_LIST_ID,
            flag,
        )
        for member in MEMBERS
    ]
    video = builder.block(
        "teachableMachine_videoToggle",
        parent=flag,
        prefix="video_on",
    )
    video_menu = builder.block(
        "teachableMachine_menu_VIDEO_STATE",
        parent=video,
        fields={"VIDEO_STATE": ["on", None]},
        shadow=True,
        prefix="video_menu",
    )
    builder.blocks[video]["inputs"] = {"VIDEO_STATE": [1, video_menu]}
    transparency = builder.block(
        "teachableMachine_setVideoTransparency",
        parent=flag,
        inputs={"TRANSPARENCY": builder.number_input(35)},
        prefix="video_transparency",
    )
    use_model = builder.block(
        "teachableMachine_useModelBlock",
        parent=flag,
        inputs={"MODEL_URL": builder.text_input(MODEL_URL)},
        prefix="use_model",
    )
    load_wait = builder.wait_seconds(MODEL_LOAD_SECONDS, flag, prefix="load_wait")
    welcome = builder.say(
        "Chuan bi cham cong lan luot tung nguoi. Moi nguoi co 15 giay.", 3, flag
    )

    turn_starts: list[str] = []
    turn_ends: list[str] = []
    for member in MEMBERS:
        first, last = build_member_turn(builder, member, flag)
        turn_starts.append(first)
        turn_ends.append(last)

    for index in range(len(turn_starts) - 1):
        builder.link(turn_ends[index], turn_starts[index + 1])

    final_report = build_final_report(builder, turn_ends[-1])

    builder.link(
        flag,
        *initializers,
        clear_list,
        *list_initializers,
        video,
        transparency,
        use_model,
        load_wait,
        welcome,
    )
    builder.link(welcome, turn_starts[0])
    builder.link(turn_ends[-1], final_report)

    comments = {
        "model_comment": {
            "blockId": use_model,
            "x": 420,
            "y": 80,
            "width": 300,
            "height": 150,
            "minimized": False,
            "text": (
                "Dan link Teachable Machine. Ten class phai dung: An, Binh, Chi. "
                "Chuong trinh goi lan luot tung nguoi, moi nguoi 15 giay nhin camera."
            ),
        }
    }

    stage_asset, sprite_asset = create_assets()
    stage_name, _ = stage_asset
    sprite_name, _ = sprite_asset
    stage_md5 = stage_name.removesuffix(".svg")
    sprite_md5 = sprite_name.removesuffix(".svg")
    attendance_list = [MEMBER_STATUS[member][0] for member in MEMBERS]

    return {
        "targets": [
            {
                "isStage": True,
                "name": "Stage",
                "variables": variables,
                "lists": {
                    ATTENDANCE_LIST_ID: [ATTENDANCE_LIST_NAME, attendance_list],
                },
                "broadcasts": {},
                "blocks": {},
                "comments": {},
                "currentCostume": 0,
                "costumes": [
                    {
                        "assetId": stage_md5,
                        "name": "Bang cham cong",
                        "md5ext": stage_name,
                        "dataFormat": "svg",
                        "rotationCenterX": 240,
                        "rotationCenterY": 180,
                    }
                ],
                "sounds": [],
                "volume": 100,
                "layerOrder": 0,
                "tempo": 60,
                "videoTransparency": 35,
                "videoState": "on",
                "textToSpeechLanguage": None,
            },
            {
                "isStage": False,
                "name": "Cham cong",
                "variables": {},
                "lists": {},
                "broadcasts": {},
                "blocks": builder.blocks,
                "comments": comments,
                "currentCostume": 0,
                "costumes": [
                    {
                        "assetId": sprite_md5,
                        "name": "Nhan vien",
                        "bitmapResolution": 1,
                        "md5ext": sprite_name,
                        "dataFormat": "svg",
                        "rotationCenterX": 95,
                        "rotationCenterY": 95,
                    }
                ],
                "sounds": [],
                "volume": 100,
                "layerOrder": 1,
                "visible": True,
                "x": 0,
                "y": -15,
                "size": 65,
                "direction": 90,
                "draggable": False,
                "rotationStyle": "all around",
            },
        ],
        "monitors": [
            {
                "id": "current_var",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "nguoi_dang_cho"},
                "spriteName": None,
                "value": "",
                "width": 0,
                "height": 0,
                "x": 10,
                "y": 10,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 100,
                "isDiscrete": True,
            },
            {
                "id": "person_time_var",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "person_time"},
                "spriteName": None,
                "value": SECONDS_PER_PERSON,
                "width": 0,
                "height": 0,
                "x": 10,
                "y": 40,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": SECONDS_PER_PERSON,
                "isDiscrete": True,
            },
            {
                "id": ATTENDANCE_LIST_ID,
                "mode": "list",
                "opcode": "data_listcontents",
                "params": {"LIST": ATTENDANCE_LIST_NAME},
                "spriteName": None,
                "value": attendance_list,
                "width": 0,
                "height": 0,
                "x": 292,
                "y": 8,
                "visible": True,
            },
            {
                "id": "prediction_monitor",
                "mode": "default",
                "opcode": "teachableMachine_modelPrediction",
                "params": {},
                "spriteName": "Cham cong",
                "value": "",
                "width": 0,
                "height": 0,
                "x": 10,
                "y": 70,
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
            "agent": "Cursor - RAISE Playground attendance project",
        },
    }


def validate_execution_chain(project: dict) -> None:
    blocks = project["targets"][1]["blocks"]
    flag = next(k for k, v in blocks.items() if v["opcode"] == "event_whenflagclicked")
    visited = set()
    current = flag
    opcodes: list[str] = []
    while current and current not in visited:
        visited.add(current)
        opcodes.append(blocks[current]["opcode"])
        current = blocks[current].get("next")
    if "control_repeat_until" not in opcodes:
        raise ValueError("Attendance loop missing from main script chain")
    if opcodes.index("control_repeat_until") > opcodes.index("teachableMachine_useModelBlock"):
        return
    raise ValueError("Attendance loop appears before model load")


def main() -> None:
    project = build_project()
    validate_execution_chain(project)
    stage_asset, sprite_asset = create_assets()
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "project.json",
            json.dumps(project, ensure_ascii=False, separators=(",", ":")),
        )
        archive.writestr(*stage_asset)
        archive.writestr(*sprite_asset)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
