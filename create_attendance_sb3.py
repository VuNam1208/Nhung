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
ATTENDANCE_SECONDS = 15
ATTENDANCE_LIST_ID = "attendance_list_id"
ATTENDANCE_LIST_NAME = "danh_sach_cham_cong"
MEMBER_STATUS = {
    "An": ("An: chua den", "An: da den", 1),
    "Binh": ("Binh: chua den", "Binh: da den", 2),
    "Chi": ("Chi: chua den", "Chi: da den", 3),
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
        next_block: str | None = None,
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
            "next": next_block,
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
<text x="240" y="320" text-anchor="middle" font-family="Arial" font-size="15" fill="#555">Nhin vao camera trong 15 giay</text>
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


def build_project() -> dict:
    builder = ProjectBuilder()
    variables = {
        "time_var": ["time", ATTENDANCE_SECONDS],
        "done_var": ["done", 0],
        "an_var": ["An_den", 0],
        "binh_var": ["Binh_den", 0],
        "chi_var": ["Chi_den", 0],
        "result_var": ["result", ""],
    }
    member_variables = {
        "An": ("An_den", "an_var"),
        "Binh": ("Binh_den", "binh_var"),
        "Chi": ("Chi_den", "chi_var"),
    }

    flag = builder.block(
        "event_whenflagclicked",
        top_level=True,
        x=35,
        y=35,
        prefix="green_flag",
    )
    initializers = [
        builder.set_variable("time", "time_var", ATTENDANCE_SECONDS, flag),
        builder.set_variable("done", "done_var", 0, flag),
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
    welcome = builder.say(
        "BAT DAU CHAM CONG - Nhin vao camera trong 15 giay!", 2, flag
    )

    repeat = builder.block("control_repeat_until", parent=flag, prefix="countdown")
    timer_is_zero = builder.equals_variable("time", "time_var", 0, repeat)
    wait = builder.block(
        "control_wait",
        parent=repeat,
        inputs={"DURATION": builder.number_input(1)},
        prefix="wait",
    )
    decrement = builder.block(
        "data_changevariableby",
        parent=wait,
        inputs={"VALUE": builder.number_input(-1)},
        fields={"VARIABLE": ["time", "time_var"]},
        prefix="decrement_time",
    )
    builder.link(wait, decrement)
    builder.blocks[repeat]["inputs"] = {
        "CONDITION": [2, timer_is_zero],
        "SUBSTACK": [2, wait],
    }
    finish = builder.set_variable("done", "done_var", 1, repeat)

    final_if = builder.block("control_if_else", parent=finish, prefix="final_check")
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
        prefix="and",
    )
    builder.blocks[and_left]["parent"] = and_all
    full_message = builder.say("Moi nguoi da den day du!", 4, final_if)

    missing_start = builder.set_variable(
        "result", "result_var", "Vang: ", final_if
    )
    missing_checks: list[str] = []
    previous = missing_start
    for member in MEMBERS:
        variable_name, variable_id = member_variables[member]
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

    builder.link(
        flag,
        *initializers,
        clear_list,
        *list_initializers,
        video,
        transparency,
        use_model,
        welcome,
        repeat,
        finish,
        final_if,
    )

    comments = {
        "model_comment": {
            "blockId": use_model,
            "x": 420,
            "y": 80,
            "width": 280,
            "height": 110,
            "minimized": False,
            "text": (
                "Thay noi dung trong use model bang link Teachable Machine "
                "cua ban. Model can co 3 class dung ten: An, Binh, Chi."
            ),
        }
    }

    for index, member in enumerate(MEMBERS):
        variable_name, variable_id = member_variables[member]
        hat = builder.block(
            "teachableMachine_whenModelMatches",
            fields={"CLASS_NAME": [member, None]},
            top_level=True,
            x=760,
            y=35 + index * 245,
            prefix=f"detect_{member}",
        )
        outer_if = builder.block("control_if", parent=hat, prefix="if_open")
        is_open = builder.equals_variable("done", "done_var", 0, outer_if)
        inner_if = builder.block("control_if", parent=outer_if, prefix="if_new")
        is_new = builder.equals_variable(variable_name, variable_id, 0, inner_if)
        mark_present = builder.set_variable(variable_name, variable_id, 1, inner_if)
        update_list = builder.replace_list_item(
            MEMBER_STATUS[member][2],
            MEMBER_STATUS[member][1],
            ATTENDANCE_LIST_NAME,
            ATTENDANCE_LIST_ID,
            mark_present,
        )
        announce = builder.say(f"{member} da den!", 2, update_list)
        builder.link(mark_present, update_list, announce)
        builder.blocks[inner_if]["inputs"] = {
            "CONDITION": [2, is_new],
            "SUBSTACK": [2, mark_present],
        }
        builder.blocks[outer_if]["inputs"] = {
            "CONDITION": [2, is_open],
            "SUBSTACK": [2, inner_if],
        }
        builder.link(hat, outer_if)

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
                "id": "time_var",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "time"},
                "spriteName": None,
                "value": ATTENDANCE_SECONDS,
                "width": 0,
                "height": 0,
                "x": 10,
                "y": 10,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": ATTENDANCE_SECONDS,
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
        ],
        "extensions": ["teachableMachine"],
        "meta": {
            "semver": "3.0.0",
            "vm": "11.1.0",
            "agent": "Cursor - RAISE Playground attendance project",
        },
    }


def main() -> None:
    project = build_project()
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
