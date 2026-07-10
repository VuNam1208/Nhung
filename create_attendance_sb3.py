#!/usr/bin/env python3
"""Sequential attendance - same detection as working Trang version."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

OUTPUT = Path(__file__).with_name("cham-cong-teachable-machine.sb3")
MODEL_URL = "https://teachablemachine.withgoogle.com/models/Xn7QBPSIY/"
MEMBERS = ("Trang", "Thỏ", "rắn")
SECONDS = 5
LIST_ID = "list1"
LIST_NAME = "Danh sách chấm công"


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
        shadow: bool = False,
        top: bool = False,
        x: int = 0,
        y: int = 0,
        prefix: str = "b",
    ) -> str:
        bid = self.nid(prefix)
        block = {
            "opcode": opcode,
            "next": None,
            "parent": parent,
            "inputs": inputs or {},
            "fields": fields or {},
            "shadow": shadow,
            "topLevel": top,
        }
        if top:
            block["x"] = x
            block["y"] = y
        self.blocks[bid] = block
        return bid

    def text(self, v: str) -> list:
        return [1, [10, v]]

    def num(self, v: int | float) -> list:
        return [1, [4, str(v)]]

    def chain(self, *ids: str) -> None:
        for a, c in zip(ids, ids[1:]):
            self.blocks[a]["next"] = c
            self.blocks[c]["parent"] = a


def svg(data: bytes) -> tuple[str, bytes]:
    return hashlib.md5(data).hexdigest() + ".svg", data


def costume(md5ext: str, name: str, cx: int, cy: int) -> dict:
    return {
        "assetId": md5ext.removesuffix(".svg"),
        "name": name,
        "bitmapResolution": 1,
        "md5ext": md5ext,
        "dataFormat": "svg",
        "rotationCenterX": cx,
        "rotationCenterY": cy,
    }


def item_of_list(b: B, index: int, parent: str) -> str:
    block = b.add(
        "data_itemoflist",
        parent=parent,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix="item",
    )
    b.blocks[block]["inputs"] = {"INDEX": b.num(index)}
    return block


def item_equals(b: B, index: int, value: str | int, parent: str) -> str:
    eq = b.add("operator_equals", parent=parent, prefix="eq")
    item = item_of_list(b, index, eq)
    rhs = b.num(value) if isinstance(value, int) else b.text(value)
    b.blocks[eq]["inputs"] = {"OPERAND1": [2, item], "OPERAND2": rhs}
    return eq


def build_one_turn(b: B, name: str, index: int) -> tuple[str, str]:
    """Exact same detect style as working project, for one person."""
    set_luot = b.add(
        "data_setvariableto",
        fields={"VARIABLE": ["luot", "luot_var"]},
        inputs={"VALUE": b.text(name)},
        prefix=f"luot{index}",
    )
    set_time = b.add(
        "data_setvariableto",
        parent=set_luot,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": b.num(SECONDS)},
        prefix=f"time{index}",
    )
    say_luot = b.add(
        "looks_sayforsecs",
        parent=set_time,
        inputs={
            "MESSAGE": b.text(f"Den luot {name} - nhin camera!"),
            "SECS": b.num(1),
        },
        prefix=f"say{index}",
    )

    # repeat until time = 0
    loop = b.add("control_repeat_until", parent=say_luot, prefix=f"loop{index}")
    time0 = b.add("operator_equals", parent=loop, prefix=f"t0{index}")
    tvar = b.add(
        "data_variable",
        parent=time0,
        fields={"VARIABLE": ["time", "time_var"]},
        prefix=f"tv{index}",
    )
    b.blocks[time0]["inputs"] = {"OPERAND1": [2, tvar], "OPERAND2": b.num(0)}

    # if <prediction is name> then
    if_pred = b.add("control_if", parent=loop, prefix=f"ip{index}")
    pred = b.add(
        "teachableMachine_modelMatches",
        parent=if_pred,
        fields={"CLASS_NAME": [name, None]},
        prefix=f"pred{index}",
    )
    # if <item index = 0> then
    if_empty = b.add("control_if", parent=if_pred, prefix=f"ie{index}")
    empty = item_equals(b, index, 0, if_empty)
    say_hi = b.add(
        "looks_sayforsecs",
        parent=if_empty,
        inputs={"MESSAGE": b.text(f"Xin chao {name}!"), "SECS": b.num(1)},
        prefix=f"hi{index}",
    )
    replace = b.add(
        "data_replaceitemoflist",
        parent=say_hi,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix=f"rp{index}",
    )
    b.blocks[replace]["inputs"] = {
        "INDEX": b.num(index),
        "ITEM": b.text(name),
    }
    b.chain(say_hi, replace)
    b.blocks[if_empty]["inputs"] = {
        "CONDITION": [2, empty],
        "SUBSTACK": [2, say_hi],
    }
    b.blocks[if_pred]["inputs"] = {
        "CONDITION": [2, pred],
        "SUBSTACK": [2, if_empty],
    }

    wait1 = b.add(
        "control_wait",
        parent=if_pred,
        inputs={"DURATION": b.num(1)},
        prefix=f"w{index}",
    )
    dec = b.add(
        "data_changevariableby",
        parent=wait1,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": b.num(-1)},
        prefix=f"dec{index}",
    )
    b.chain(if_pred, wait1, dec)
    b.blocks[loop]["inputs"] = {
        "CONDITION": [2, time0],
        "SUBSTACK": [2, if_pred],
    }

    b.chain(set_luot, set_time, say_luot, loop)
    return set_luot, loop


def build() -> dict:
    b = B()

    flag = b.add("event_whenflagclicked", top=True, x=40, y=40, prefix="flag")
    clear = b.add(
        "data_deletealloflist",
        parent=flag,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix="clear",
    )
    adds = []
    prev = clear
    for i in range(3):
        a = b.add(
            "data_addtolist",
            parent=prev,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            inputs={"ITEM": b.num(0)},
            prefix=f"add{i}",
        )
        adds.append(a)
        prev = a

    use = b.add(
        "teachableMachine_useModelBlock",
        parent=prev,
        inputs={"MODEL_URL": b.text(MODEL_URL)},
        prefix="use",
    )
    von = b.add("teachableMachine_videoToggle", parent=use, prefix="von")
    vonm = b.add(
        "teachableMachine_menu_VIDEO_STATE",
        parent=von,
        fields={"VIDEO_STATE": ["on", None]},
        shadow=True,
        prefix="vonm",
    )
    b.blocks[von]["inputs"] = {"VIDEO_STATE": [1, vonm]}
    trans = b.add(
        "teachableMachine_setVideoTransparency",
        parent=von,
        inputs={"TRANSPARENCY": b.num(20)},
        prefix="trans",
    )
    load = b.add(
        "control_wait",
        parent=trans,
        inputs={"DURATION": b.num(2)},
        prefix="load",
    )

    # Build 3 turns then link: load -> turn1 -> turn2 -> turn3 -> final
    turn_blocks = [build_one_turn(b, name, i) for i, name in enumerate(MEMBERS, start=1)]

    # final report
    if_full = b.add("control_if_else", prefix="full")
    filled = []
    for i, name in enumerate(MEMBERS, start=1):
        filled.append(item_equals(b, i, name, if_full))
    and1 = b.add("operator_and", parent=if_full, prefix="a1")
    b.blocks[and1]["inputs"] = {"OPERAND1": [2, filled[0]], "OPERAND2": [2, filled[1]]}
    and2 = b.add("operator_and", parent=if_full, prefix="a2")
    b.blocks[and2]["inputs"] = {"OPERAND1": [2, and1], "OPERAND2": [2, filled[2]]}
    b.blocks[filled[0]]["parent"] = and1
    b.blocks[filled[1]]["parent"] = and1
    b.blocks[and1]["parent"] = and2
    b.blocks[filled[2]]["parent"] = and2

    say_full = b.add(
        "looks_sayforsecs",
        parent=if_full,
        inputs={"MESSAGE": b.text("Moi nguoi da den day du"), "SECS": b.num(3)},
        prefix="sayfull",
    )

    misses = []
    for i, name in enumerate(MEMBERS, start=1):
        parent = misses[-1] if misses else if_full
        if_m = b.add("control_if", parent=parent, prefix=f"m{i}")
        still0 = item_equals(b, i, 0, if_m)
        say_m = b.add(
            "looks_sayforsecs",
            parent=if_m,
            inputs={"MESSAGE": b.text(f"Vang {name}"), "SECS": b.num(2)},
            prefix=f"sm{i}",
        )
        b.blocks[if_m]["inputs"] = {
            "CONDITION": [2, still0],
            "SUBSTACK": [2, say_m],
        }
        misses.append(if_m)
    b.chain(*misses)
    b.blocks[if_full]["inputs"] = {
        "CONDITION": [2, and2],
        "SUBSTACK": [2, say_full],
        "SUBSTACK2": [2, misses[0]],
    }

    # Link everything carefully
    b.chain(flag, clear, *adds, use, von, trans, load)
    b.chain(load, turn_blocks[0][0])
    b.chain(turn_blocks[0][1], turn_blocks[1][0])
    b.chain(turn_blocks[1][1], turn_blocks[2][0])
    b.chain(turn_blocks[2][1], if_full)

    comments = {
        "c1": {
            "blockId": use,
            "x": 380,
            "y": 40,
            "width": 220,
            "height": 80,
            "minimized": False,
            "text": "Trang 5s -> Tho 5s -> ran 5s. Bam co xanh.",
        }
    }

    stage_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect width="480" height="360" fill="#e3f2fd"/></svg>"""
    sprite_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="140"><circle cx="48" cy="36" r="24" fill="#f5cba7"/><rect x="24" y="62" width="48" height="60" rx="10" fill="#5d4037"/></svg>"""
    stage_f, sprite_f = svg(stage_svg), svg(sprite_svg)

    return {
        "targets": [
            {
                "isStage": True,
                "name": "Stage",
                "variables": {
                    "time_var": ["time", SECONDS],
                    "luot_var": ["luot", ""],
                },
                "lists": {LIST_ID: [LIST_NAME, [0, 0, 0]]},
                "broadcasts": {},
                "blocks": {},
                "comments": {},
                "currentCostume": 0,
                "costumes": [costume(stage_f[0], "backdrop", 240, 180)],
                "sounds": [],
                "volume": 100,
                "layerOrder": 0,
                "tempo": 60,
                "videoTransparency": 20,
                "videoState": "on",
                "textToSpeechLanguage": None,
            },
            {
                "isStage": False,
                "name": "Avery",
                "variables": {},
                "lists": {},
                "broadcasts": {},
                "blocks": b.blocks,
                "comments": comments,
                "currentCostume": 0,
                "costumes": [costume(sprite_f[0], "Avery", 48, 70)],
                "sounds": [],
                "volume": 100,
                "layerOrder": 1,
                "visible": True,
                "x": -120,
                "y": 0,
                "size": 80,
                "direction": 90,
                "draggable": False,
                "rotationStyle": "all around",
            },
        ],
        "monitors": [
            {
                "id": "luot_var",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "luot"},
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
                "id": "time_var",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "time"},
                "spriteName": None,
                "value": SECONDS,
                "width": 0,
                "height": 0,
                "x": 10,
                "y": 40,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": SECONDS,
                "isDiscrete": True,
            },
            {
                "id": LIST_ID,
                "mode": "list",
                "opcode": "data_listcontents",
                "params": {"LIST": LIST_NAME},
                "spriteName": None,
                "value": [0, 0, 0],
                "width": 0,
                "height": 0,
                "x": 260,
                "y": 20,
                "visible": True,
            },
        ],
        "extensions": ["teachableMachine"],
        "meta": {"semver": "3.0.0", "vm": "11.1.0", "agent": "seq-simple-detect"},
        "_assets": [stage_f, sprite_f],
    }


def main() -> None:
    project = build()
    assets = project.pop("_assets")
    blocks = project["targets"][1]["blocks"]
    flag = next(k for k, v in blocks.items() if v["opcode"] == "event_whenflagclicked")
    cur, ops = flag, []
    while cur:
        ops.append(blocks[cur]["opcode"])
        cur = blocks[cur].get("next")
    assert ops.count("control_repeat_until") == 3, ops
    assert "teachableMachine_modelMatches" in {
        v["opcode"] for v in blocks.values()
    }
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "project.json",
            json.dumps(project, ensure_ascii=False, separators=(",", ":")),
        )
        for name, data in assets:
            z.writestr(name, data)
    print("Created", OUTPUT, "chain loops=", ops.count("control_repeat_until"))


if __name__ == "__main__":
    main()
