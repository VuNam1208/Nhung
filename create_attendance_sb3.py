#!/usr/bin/env python3
"""Ultra-simple attendance: green flag -> look 5s -> recognize."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

OUTPUT = Path(__file__).with_name("cham-cong-teachable-machine.sb3")
MODEL_URL = "Paste your Teachable Machine model URL here!"
MEMBERS = ("Trang", "Thỏ", "rắn")
ABSENT = ("Thu Trang", "Thỏ", "rắn")
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


def build() -> dict:
    b = B()

    # ONE script: green flag
    flag = b.add("event_whenflagclicked", top=True, x=40, y=40, prefix="flag")

    # reset list to [0,0,0]
    clear = b.add(
        "data_deletealloflist",
        parent=flag,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix="clear",
    )
    zeros = []
    prev = clear
    for i in range(3):
        z = b.add(
            "data_addtolist",
            parent=prev,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            inputs={"ITEM": b.num(0)},
            prefix=f"z{i}",
        )
        zeros.append(z)
        prev = z

    # set time = 5
    set_time = b.add(
        "data_setvariableto",
        parent=prev,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": b.num(SECONDS)},
        prefix="st",
    )

    # use model
    use = b.add(
        "teachableMachine_useModelBlock",
        parent=set_time,
        inputs={"MODEL_URL": b.text(MODEL_URL)},
        prefix="use",
    )

    # video on
    von = b.add("teachableMachine_videoToggle", parent=use, prefix="von")
    vonm = b.add(
        "teachableMachine_menu_VIDEO_STATE",
        parent=von,
        fields={"VIDEO_STATE": ["on", None]},
        shadow=True,
        prefix="vonm",
    )
    b.blocks[von]["inputs"] = {"VIDEO_STATE": [1, vonm]}

    # transparency
    trans = b.add(
        "teachableMachine_setVideoTransparency",
        parent=von,
        inputs={"TRANSPARENCY": b.num(20)},
        prefix="trans",
    )

    # wait 2s for model load
    load = b.add(
        "control_wait",
        parent=trans,
        inputs={"DURATION": b.num(2)},
        prefix="load",
    )

    # say start
    say_start = b.add(
        "looks_sayforsecs",
        parent=load,
        inputs={"MESSAGE": b.text("Nhin vao camera trong 5 giay!"), "SECS": b.num(1)},
        prefix="saystart",
    )

    # repeat until time = 0
    loop = b.add("control_repeat_until", parent=say_start, prefix="loop")
    teq = b.add("operator_equals", parent=loop, prefix="teq")
    tvar = b.add(
        "data_variable",
        parent=teq,
        fields={"VARIABLE": ["time", "time_var"]},
        prefix="tvar",
    )
    b.blocks[teq]["inputs"] = {"OPERAND1": [2, tvar], "OPERAND2": b.num(0)}

    # inside loop: check 3 people
    detects = []
    for idx, name in enumerate(MEMBERS, start=1):
        parent = detects[-1] if detects else loop
        if_pred = b.add("control_if", parent=parent, prefix=f"ip{idx}")
        pred = b.add(
            "teachableMachine_modelMatches",
            parent=if_pred,
            fields={"CLASS_NAME": [name, None]},
            prefix=f"p{idx}",
        )
        if_empty = b.add("control_if", parent=if_pred, prefix=f"ie{idx}")
        empty = b.add("operator_equals", parent=if_empty, prefix=f"ee{idx}")
        item = b.add(
            "data_itemoflist",
            parent=empty,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"it{idx}",
        )
        b.blocks[item]["inputs"] = {"INDEX": b.num(idx)}
        b.blocks[empty]["inputs"] = {"OPERAND1": [2, item], "OPERAND2": b.num(0)}
        say_hi = b.add(
            "looks_say",
            parent=if_empty,
            inputs={"MESSAGE": b.text(f"Xin chao {name}!")},
            prefix=f"hi{idx}",
        )
        replace = b.add(
            "data_replaceitemoflist",
            parent=say_hi,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"rp{idx}",
        )
        b.blocks[replace]["inputs"] = {"INDEX": b.num(idx), "ITEM": b.text(name)}
        b.chain(say_hi, replace)
        b.blocks[if_empty]["inputs"] = {
            "CONDITION": [2, empty],
            "SUBSTACK": [2, say_hi],
        }
        b.blocks[if_pred]["inputs"] = {
            "CONDITION": [2, pred],
            "SUBSTACK": [2, if_empty],
        }
        detects.append(if_pred)

    # wait 1s then time -= 1
    wait1 = b.add(
        "control_wait",
        parent=detects[-1],
        inputs={"DURATION": b.num(1)},
        prefix="w1",
    )
    tick = b.add(
        "data_changevariableby",
        parent=wait1,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": b.num(-1)},
        prefix="tick",
    )
    b.chain(*detects, wait1, tick)
    b.blocks[loop]["inputs"] = {"CONDITION": [2, teq], "SUBSTACK": [2, detects[0]]}

    # after loop: report
    if_full = b.add("control_if_else", parent=loop, prefix="full")
    nots = []
    for idx in range(1, 4):
        n = b.add("operator_not", parent=if_full, prefix=f"n{idx}")
        eq = b.add("operator_equals", parent=n, prefix=f"neq{idx}")
        it = b.add(
            "data_itemoflist",
            parent=eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"nit{idx}",
        )
        b.blocks[it]["inputs"] = {"INDEX": b.num(idx)}
        b.blocks[eq]["inputs"] = {"OPERAND1": [2, it], "OPERAND2": b.num(0)}
        b.blocks[n]["inputs"] = {"OPERAND": [2, eq]}
        nots.append(n)
    and1 = b.add("operator_and", parent=if_full, prefix="a1")
    b.blocks[and1]["inputs"] = {"OPERAND1": [2, nots[0]], "OPERAND2": [2, nots[1]]}
    and2 = b.add("operator_and", parent=if_full, prefix="a2")
    b.blocks[and2]["inputs"] = {"OPERAND1": [2, and1], "OPERAND2": [2, nots[2]]}
    b.blocks[nots[0]]["parent"] = and1
    b.blocks[nots[1]]["parent"] = and1
    b.blocks[and1]["parent"] = and2
    b.blocks[nots[2]]["parent"] = and2

    say_full = b.add(
        "looks_sayforsecs",
        parent=if_full,
        inputs={"MESSAGE": b.text("Moi nguoi da den day du"), "SECS": b.num(3)},
        prefix="sayfull",
    )

    misses = []
    for idx, label in enumerate(ABSENT, start=1):
        parent = misses[-1] if misses else if_full
        if_m = b.add("control_if", parent=parent, prefix=f"m{idx}")
        eq = b.add("operator_equals", parent=if_m, prefix=f"me{idx}")
        it = b.add(
            "data_itemoflist",
            parent=eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"mit{idx}",
        )
        b.blocks[it]["inputs"] = {"INDEX": b.num(idx)}
        b.blocks[eq]["inputs"] = {"OPERAND1": [2, it], "OPERAND2": b.num(0)}
        say_m = b.add(
            "looks_sayforsecs",
            parent=if_m,
            inputs={"MESSAGE": b.text(f"Vang {label}"), "SECS": b.num(2)},
            prefix=f"sm{idx}",
        )
        b.blocks[if_m]["inputs"] = {"CONDITION": [2, eq], "SUBSTACK": [2, say_m]}
        misses.append(if_m)
    b.chain(*misses)
    b.blocks[if_full]["inputs"] = {
        "CONDITION": [2, and2],
        "SUBSTACK": [2, say_full],
        "SUBSTACK2": [2, misses[0]],
    }

    b.chain(
        flag,
        clear,
        *zeros,
        set_time,
        use,
        von,
        trans,
        load,
        say_start,
        loop,
        if_full,
    )

    comments = {
        "c1": {
            "blockId": use,
            "x": 360,
            "y": 40,
            "width": 240,
            "height": 90,
            "minimized": False,
            "text": "Dan link model. Bam co xanh, nhin camera 5 giay. Class: Trang, Tho, ran.",
        }
    }

    stage_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect width="480" height="360" fill="#e3f2fd"/></svg>"""
    sprite_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="140"><circle cx="48" cy="36" r="24" fill="#f5cba7"/><rect x="24" y="62" width="48" height="60" rx="10" fill="#5d4037"/></svg>"""
    stage_f = svg(stage_svg)
    sprite_f = svg(sprite_svg)

    return {
        "targets": [
            {
                "isStage": True,
                "name": "Stage",
                "variables": {"time_var": ["time", SECONDS]},
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
                "id": "time_var",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "time"},
                "spriteName": None,
                "value": SECONDS,
                "width": 0,
                "height": 0,
                "x": 10,
                "y": 10,
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
            {
                "id": "pred",
                "mode": "default",
                "opcode": "teachableMachine_modelPrediction",
                "params": {},
                "spriteName": "Avery",
                "value": "",
                "width": 0,
                "height": 0,
                "x": 10,
                "y": 45,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 100,
                "isDiscrete": True,
            },
        ],
        "extensions": ["teachableMachine"],
        "meta": {"semver": "3.0.0", "vm": "11.1.0", "agent": "flag-5s-attendance"},
        "_assets": [stage_f, sprite_f],
    }


def main() -> None:
    project = build()
    assets = project.pop("_assets")
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "project.json",
            json.dumps(project, ensure_ascii=False, separators=(",", ":")),
        )
        for name, data in assets:
            z.writestr(name, data)
    print("Created", OUTPUT)


if __name__ == "__main__":
    main()
