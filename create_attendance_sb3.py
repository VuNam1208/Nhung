#!/usr/bin/env python3
"""Green flag -> look 5s -> mark attendance using model prediction equals."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

OUTPUT = Path(__file__).with_name("cham-cong-teachable-machine.sb3")
MODEL_URL = "Paste your Teachable Machine model URL here!"
# Ten class PHAI giong model prediction tren man hinh
MEMBERS = ("Trang", "Thỏ", "rắn")
ABSENT_LABELS = ("Trang", "Thỏ", "rắn")
SECONDS = 5
CHECKS_PER_SECOND = 5  # check moi 0.2s
LIST_ID = "list1"
LIST_NAME = "Danh sách chấm công"
EMPTY = "?"


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


def pred_equals(b: B, name: str, parent: str) -> str:
    """<(model prediction) = [name]> — khong dung menu class."""
    eq = b.add("operator_equals", parent=parent, prefix="eq")
    pred = b.add("teachableMachine_modelPrediction", parent=eq, prefix="pred")
    b.blocks[eq]["inputs"] = {
        "OPERAND1": [2, pred],
        "OPERAND2": b.text(name),
    }
    return eq


def build() -> dict:
    b = B()
    total_checks = SECONDS * CHECKS_PER_SECOND
    wait_each = round(1 / CHECKS_PER_SECOND, 2)

    flag = b.add("event_whenflagclicked", top=True, x=30, y=30, prefix="flag")

    clear = b.add(
        "data_deletealloflist",
        parent=flag,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix="clear",
    )
    inits = []
    prev = clear
    for i in range(3):
        add = b.add(
            "data_addtolist",
            parent=prev,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            inputs={"ITEM": b.text(EMPTY)},
            prefix=f"init{i}",
        )
        inits.append(add)
        prev = add

    set_time = b.add(
        "data_setvariableto",
        parent=prev,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": b.num(SECONDS)},
        prefix="st",
    )
    set_tick = b.add(
        "data_setvariableto",
        parent=set_time,
        fields={"VARIABLE": ["tick", "tick_var"]},
        inputs={"VALUE": b.num(0)},
        prefix="stick",
    )

    use = b.add(
        "teachableMachine_useModelBlock",
        parent=set_tick,
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
        inputs={"DURATION": b.num(3)},
        prefix="load",
    )
    say_go = b.add(
        "looks_say",
        parent=load,
        inputs={"MESSAGE": b.text("Nhin camera 5 giay!")},
        prefix="saygo",
    )

    # Lap 25 lan (5 giay x 5 lan/giay)
    rep = b.add("control_repeat", parent=say_go, prefix="rep")
    b.blocks[rep]["inputs"] = {"TIMES": b.num(total_checks)}

    # Hien prediction dang nhin thay
    show_pred = b.add("looks_say", parent=rep, prefix="showpred")
    join = b.add("operator_join", parent=show_pred, prefix="join")
    pred_val = b.add("teachableMachine_modelPrediction", parent=join, prefix="pv")
    b.blocks[join]["inputs"] = {
        "STRING1": b.text("Dang nhin: "),
        "STRING2": [2, pred_val],
    }
    b.blocks[show_pred]["inputs"] = {"MESSAGE": [2, join]}

    detects = []
    for idx, name in enumerate(MEMBERS, start=1):
        parent = detects[-1] if detects else show_pred
        if_pred = b.add("control_if", parent=parent, prefix=f"ip{idx}")
        cond = pred_equals(b, name, if_pred)
        if_empty = b.add("control_if", parent=if_pred, prefix=f"ie{idx}")
        empty_eq = b.add("operator_equals", parent=if_empty, prefix=f"ee{idx}")
        item = b.add(
            "data_itemoflist",
            parent=empty_eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"it{idx}",
        )
        b.blocks[item]["inputs"] = {"INDEX": b.num(idx)}
        b.blocks[empty_eq]["inputs"] = {
            "OPERAND1": [2, item],
            "OPERAND2": b.text(EMPTY),
        }
        replace = b.add(
            "data_replaceitemoflist",
            parent=if_empty,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"rp{idx}",
        )
        b.blocks[replace]["inputs"] = {
            "INDEX": b.num(idx),
            "ITEM": b.text(name),
        }
        hello = b.add(
            "looks_say",
            parent=replace,
            inputs={"MESSAGE": b.text(f"OK {name} da cham cong!")},
            prefix=f"hi{idx}",
        )
        b.chain(replace, hello)
        b.blocks[if_empty]["inputs"] = {
            "CONDITION": [2, empty_eq],
            "SUBSTACK": [2, replace],
        }
        b.blocks[if_pred]["inputs"] = {
            "CONDITION": [2, cond],
            "SUBSTACK": [2, if_empty],
        }
        detects.append(if_pred)

    # tick dem giay: moi 5 lan check thi time -= 1
    wait = b.add(
        "control_wait",
        parent=detects[-1],
        inputs={"DURATION": b.num(wait_each)},
        prefix="wait",
    )
    add_tick = b.add(
        "data_changevariableby",
        parent=wait,
        fields={"VARIABLE": ["tick", "tick_var"]},
        inputs={"VALUE": b.num(1)},
        prefix="addtick",
    )
    if_sec = b.add("control_if", parent=add_tick, prefix="ifsec")
    tick_eq = b.add("operator_equals", parent=if_sec, prefix="tickeq")
    tick_var = b.add(
        "data_variable",
        parent=tick_eq,
        fields={"VARIABLE": ["tick", "tick_var"]},
        prefix="tickv",
    )
    b.blocks[tick_eq]["inputs"] = {
        "OPERAND1": [2, tick_var],
        "OPERAND2": b.num(CHECKS_PER_SECOND),
    }
    reset_tick = b.add(
        "data_setvariableto",
        parent=if_sec,
        fields={"VARIABLE": ["tick", "tick_var"]},
        inputs={"VALUE": b.num(0)},
        prefix="rtick",
    )
    dec_time = b.add(
        "data_changevariableby",
        parent=reset_tick,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": b.num(-1)},
        prefix="dectime",
    )
    b.chain(reset_tick, dec_time)
    b.blocks[if_sec]["inputs"] = {
        "CONDITION": [2, tick_eq],
        "SUBSTACK": [2, reset_tick],
    }

    b.chain(show_pred, *detects, wait, add_tick, if_sec)
    b.blocks[rep]["inputs"]["SUBSTACK"] = [2, show_pred]

    # Ket qua
    if_full = b.add("control_if_else", parent=rep, prefix="full")
    filled = []
    for idx, name in enumerate(MEMBERS, start=1):
        eq = b.add("operator_equals", parent=if_full, prefix=f"fe{idx}")
        item = b.add(
            "data_itemoflist",
            parent=eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"fi{idx}",
        )
        b.blocks[item]["inputs"] = {"INDEX": b.num(idx)}
        b.blocks[eq]["inputs"] = {
            "OPERAND1": [2, item],
            "OPERAND2": b.text(name),
        }
        filled.append(eq)
    and1 = b.add("operator_and", parent=if_full, prefix="and1")
    b.blocks[and1]["inputs"] = {"OPERAND1": [2, filled[0]], "OPERAND2": [2, filled[1]]}
    and2 = b.add("operator_and", parent=if_full, prefix="and2")
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
    for idx, label in enumerate(ABSENT_LABELS, start=1):
        parent = misses[-1] if misses else if_full
        if_m = b.add("control_if", parent=parent, prefix=f"m{idx}")
        eq = b.add("operator_equals", parent=if_m, prefix=f"me{idx}")
        item = b.add(
            "data_itemoflist",
            parent=eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"mi{idx}",
        )
        b.blocks[item]["inputs"] = {"INDEX": b.num(idx)}
        b.blocks[eq]["inputs"] = {
            "OPERAND1": [2, item],
            "OPERAND2": b.text(EMPTY),
        }
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
        *inits,
        set_time,
        set_tick,
        use,
        von,
        trans,
        load,
        say_go,
        rep,
        if_full,
    )

    comments = {
        "c1": {
            "blockId": use,
            "x": 380,
            "y": 30,
            "width": 260,
            "height": 110,
            "minimized": False,
            "text": (
                "BAT BUOC: dan link Teachable Machine vao day. "
                "Ten class phai dung: Trang, Tho, ran. "
                "Bam co xanh, doi 3 giay, nhin camera."
            ),
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
                    "tick_var": ["tick", 0],
                },
                "lists": {LIST_ID: [LIST_NAME, [EMPTY, EMPTY, EMPTY]]},
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
                "value": [EMPTY, EMPTY, EMPTY],
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
        "meta": {"semver": "3.0.0", "vm": "11.1.0", "agent": "pred-equals-5s"},
        "_assets": [stage_f, sprite_f],
    }


def main() -> None:
    project = build()
    assets = project.pop("_assets")
    blocks = project["targets"][1]["blocks"]
    assert any(v["opcode"] == "teachableMachine_modelPrediction" for v in blocks.values())
    assert any(v["opcode"] == "control_repeat" for v in blocks.values())
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
