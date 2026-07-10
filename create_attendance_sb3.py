#!/usr/bin/env python3
"""Simple attendance SB3 matching the working Thu Trang sample."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

OUTPUT = Path(__file__).with_name("cham-cong-teachable-machine.sb3")
MODEL_URL = "Paste your Teachable Machine model URL here!"
MEMBERS = ("Trang", "Thỏ", "rắn")
ABSENT_NAMES = ("Thu Trang", "Thỏ", "rắn")
SECONDS = 10
LIST_ID = "list1"
LIST_NAME = "Danh sách chấm công"
MSG_START = "Thời gian chấm công"
MSG_END = "Hết giờ"


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
        shadow: bool = False,
        top: bool = False,
        x: int = 0,
        y: int = 0,
        prefix: str = "b",
    ) -> str:
        bid = self.id(prefix)
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
        for a, b in zip(ids, ids[1:]):
            self.blocks[a]["next"] = b
            self.blocks[b]["parent"] = a


def svg_asset(svg: bytes) -> tuple[str, bytes]:
    name = hashlib.md5(svg).hexdigest() + ".svg"
    return name, svg


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

    # ===== Avery: green flag =====
    flag = b.add("event_whenflagclicked", top=True, x=40, y=40, prefix="flag")
    use = b.add(
        "teachableMachine_useModelBlock",
        parent=flag,
        inputs={"MODEL_URL": b.text(MODEL_URL)},
        prefix="use",
    )
    trans = b.add(
        "teachableMachine_setVideoTransparency",
        parent=use,
        inputs={"TRANSPARENCY": b.num(20)},
        prefix="trans",
    )
    b.chain(flag, use, trans)

    # ===== Avery: space = video off =====
    space = b.add(
        "event_whenkeypressed",
        fields={"KEY_OPTION": ["space", None]},
        top=True,
        x=40,
        y=180,
        prefix="space",
    )
    voff = b.add("teachableMachine_videoToggle", parent=space, prefix="voff")
    voff_menu = b.add(
        "teachableMachine_menu_VIDEO_STATE",
        parent=voff,
        fields={"VIDEO_STATE": ["off", None]},
        shadow=True,
        prefix="voffm",
    )
    b.blocks[voff]["inputs"] = {"VIDEO_STATE": [1, voff_menu]}
    b.chain(space, voff)

    # ===== Avery: key a = start attendance =====
    key_a = b.add(
        "event_whenkeypressed",
        fields={"KEY_OPTION": ["a", None]},
        top=True,
        x=40,
        y=280,
        prefix="keya",
    )
    clear = b.add(
        "data_deletealloflist",
        parent=key_a,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix="clear",
    )
    add0 = []
    prev = clear
    for i in range(3):
        add = b.add(
            "data_addtolist",
            parent=prev,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            inputs={"ITEM": b.num(0)},
            prefix=f"z{i}",
        )
        add0.append(add)
        prev = add
    say_bang = b.add(
        "looks_sayforsecs",
        parent=prev,
        inputs={"MESSAGE": b.text("Bảng chấm công"), "SECS": b.num(2)},
        prefix="saybang",
    )
    von = b.add("teachableMachine_videoToggle", parent=say_bang, prefix="von")
    von_menu = b.add(
        "teachableMachine_menu_VIDEO_STATE",
        parent=von,
        fields={"VIDEO_STATE": ["on", None]},
        shadow=True,
        prefix="vonm",
    )
    b.blocks[von]["inputs"] = {"VIDEO_STATE": [1, von_menu]}
    start = b.add(
        "event_broadcast",
        parent=von,
        prefix="start",
    )
    b.blocks[start]["inputs"] = {
        "BROADCAST_INPUT": [1, [11, MSG_START, MSG_START]]
    }
    b.chain(key_a, clear, *add0, say_bang, von, start)

    # ===== Avery: when start -> loop detect until time=0 =====
    recv_start = b.add(
        "event_whenbroadcastreceived",
        fields={"BROADCAST_OPTION": [MSG_START, MSG_START]},
        top=True,
        x=420,
        y=40,
        prefix="rs",
    )
    wait_model = b.add(
        "control_wait",
        parent=recv_start,
        inputs={"DURATION": b.num(1)},
        prefix="wm",
    )
    loop = b.add("control_repeat_until", parent=wait_model, prefix="loop")
    time_eq = b.add("operator_equals", parent=loop, prefix="teq")
    time_var = b.add(
        "data_variable",
        parent=time_eq,
        fields={"VARIABLE": ["time", "time_var"]},
        prefix="tvar",
    )
    b.blocks[time_eq]["inputs"] = {
        "OPERAND1": [2, time_var],
        "OPERAND2": b.num(0),
    }

    detect_ids = []
    for idx, name in enumerate(MEMBERS, start=1):
        parent = detect_ids[-1] if detect_ids else loop
        if_pred = b.add("control_if", parent=parent, prefix=f"ip{idx}")
        pred = b.add(
            "teachableMachine_modelMatches",
            parent=if_pred,
            fields={"CLASS_NAME": [name, None]},
            prefix=f"p{idx}",
        )
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
            "OPERAND2": b.num(0),
        }
        say_hi = b.add(
            "looks_sayforsecs",
            parent=if_empty,
            inputs={"MESSAGE": b.text(f"Xin chào {name}!"), "SECS": b.num(1)},
            prefix=f"hi{idx}",
        )
        replace = b.add(
            "data_replaceitemoflist",
            parent=say_hi,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"rp{idx}",
        )
        b.blocks[replace]["inputs"] = {
            "INDEX": b.num(idx),
            "ITEM": b.text(name),
        }
        b.chain(say_hi, replace)
        b.blocks[if_empty]["inputs"] = {
            "CONDITION": [2, empty_eq],
            "SUBSTACK": [2, say_hi],
        }
        b.blocks[if_pred]["inputs"] = {
            "CONDITION": [2, pred],
            "SUBSTACK": [2, if_empty],
        }
        detect_ids.append(if_pred)

    pause = b.add(
        "control_wait",
        parent=detect_ids[-1],
        inputs={"DURATION": b.num(0.2)},
        prefix="pause",
    )
    b.chain(*detect_ids, pause)
    b.blocks[loop]["inputs"] = {
        "CONDITION": [2, time_eq],
        "SUBSTACK": [2, detect_ids[0]],
    }
    b.chain(recv_start, wait_model, loop)

    # ===== Avery: when end -> report =====
    recv_end = b.add(
        "event_whenbroadcastreceived",
        fields={"BROADCAST_OPTION": [MSG_END, MSG_END]},
        top=True,
        x=420,
        y=420,
        prefix="re",
    )
    # count present: how many slots are not 0
    # if all 3 filled
    if_full = b.add("control_if_else", parent=recv_end, prefix="full")
    # item1 != 0 and item2 != 0 and item3 != 0
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
        inputs={"MESSAGE": b.text("Mọi người đã đến đầy đủ"), "SECS": b.num(3)},
        prefix="sayfull",
    )

    miss_ids = []
    for idx, label in enumerate(ABSENT_NAMES, start=1):
        parent = miss_ids[-1] if miss_ids else if_full
        if_miss = b.add("control_if", parent=parent, prefix=f"m{idx}")
        eq = b.add("operator_equals", parent=if_miss, prefix=f"me{idx}")
        it = b.add(
            "data_itemoflist",
            parent=eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"mit{idx}",
        )
        b.blocks[it]["inputs"] = {"INDEX": b.num(idx)}
        b.blocks[eq]["inputs"] = {"OPERAND1": [2, it], "OPERAND2": b.num(0)}
        say_miss = b.add(
            "looks_sayforsecs",
            parent=if_miss,
            inputs={"MESSAGE": b.text(f"Vắng {label}"), "SECS": b.num(2)},
            prefix=f"sm{idx}",
        )
        b.blocks[if_miss]["inputs"] = {
            "CONDITION": [2, eq],
            "SUBSTACK": [2, say_miss],
        }
        miss_ids.append(if_miss)
    b.chain(*miss_ids)
    b.blocks[if_full]["inputs"] = {
        "CONDITION": [2, and2],
        "SUBSTACK": [2, say_full],
        "SUBSTACK2": [2, miss_ids[0]],
    }
    b.chain(recv_end, if_full)

    avery_blocks = b.blocks
    comments = {
        "c1": {
            "blockId": use,
            "x": 280,
            "y": 40,
            "width": 260,
            "height": 100,
            "minimized": False,
            "text": "Dan link Teachable Machine. Class: Trang, Tho, ran. Bam co xanh, roi bam phim a.",
        }
    }

    # ===== Bang dem: countdown =====
    c = B()
    recv = c.add(
        "event_whenbroadcastreceived",
        fields={"BROADCAST_OPTION": [MSG_START, MSG_START]},
        top=True,
        x=40,
        y=40,
        prefix="cr",
    )
    set_t = c.add(
        "data_setvariableto",
        parent=recv,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": c.num(SECONDS)},
        prefix="st",
    )
    rep = c.add("control_repeat", parent=set_t, prefix="rep")
    c.blocks[rep]["inputs"] = {"TIMES": c.num(SECONDS)}
    w = c.add("control_wait", parent=rep, inputs={"DURATION": c.num(1)}, prefix="cw")
    ch = c.add(
        "data_changevariableby",
        parent=w,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": c.num(-1)},
        prefix="ch",
    )
    c.chain(w, ch)
    c.blocks[rep]["inputs"]["SUBSTACK"] = [2, w]
    end = c.add("event_broadcast", parent=rep, prefix="end")
    c.blocks[end]["inputs"] = {
        "BROADCAST_INPUT": [1, [11, MSG_END, MSG_END]]
    }
    c.chain(recv, set_t, rep, end)
    counter_blocks = c.blocks

    stage_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect width="480" height="360" fill="#b3e5fc"/></svg>"""
    avery_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="140"><circle cx="48" cy="36" r="24" fill="#f5cba7"/><rect x="24" y="62" width="48" height="60" rx="10" fill="#5d4037"/></svg>"""
    counter_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="70"><rect width="100" height="70" rx="8" fill="#1b5e20"/><text x="50" y="46" text-anchor="middle" font-family="Arial" font-size="28" fill="#69f0ae">10</text></svg>"""
    stage_f = svg_asset(stage_svg)
    avery_f = svg_asset(avery_svg)
    counter_f = svg_asset(counter_svg)

    return {
        "targets": [
            {
                "isStage": True,
                "name": "Stage",
                "variables": {"time_var": ["time", SECONDS]},
                "lists": {LIST_ID: [LIST_NAME, [0, 0, 0]]},
                "broadcasts": {MSG_START: MSG_START, MSG_END: MSG_END},
                "blocks": {},
                "comments": {},
                "currentCostume": 0,
                "costumes": [costume(stage_f[0], "backdrop", 240, 180)],
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
                "costumes": [costume(avery_f[0], "Avery", 48, 70)],
                "sounds": [],
                "volume": 100,
                "layerOrder": 2,
                "visible": True,
                "x": -140,
                "y": -10,
                "size": 90,
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
                "costumes": [costume(counter_f[0], "dem", 50, 35)],
                "sounds": [],
                "volume": 100,
                "layerOrder": 1,
                "visible": True,
                "x": 140,
                "y": 110,
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
                "value": [0, 0, 0],
                "width": 0,
                "height": 0,
                "x": 260,
                "y": 20,
                "visible": True,
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
                "x": 140,
                "y": 70,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": SECONDS,
                "isDiscrete": True,
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
                "y": 10,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 100,
                "isDiscrete": True,
            },
        ],
        "extensions": ["teachableMachine"],
        "meta": {"semver": "3.0.0", "vm": "11.1.0", "agent": "simple-attendance"},
    }


def main() -> None:
    project = build()
    stage_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect width="480" height="360" fill="#b3e5fc"/></svg>"""
    avery_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="140"><circle cx="48" cy="36" r="24" fill="#f5cba7"/><rect x="24" y="62" width="48" height="60" rx="10" fill="#5d4037"/></svg>"""
    counter_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="70"><rect width="100" height="70" rx="8" fill="#1b5e20"/><text x="50" y="46" text-anchor="middle" font-family="Arial" font-size="28" fill="#69f0ae">10</text></svg>"""
    files = [svg_asset(stage_svg), svg_asset(avery_svg), svg_asset(counter_svg)]
    # ensure costume md5ext matches written files
    project["targets"][0]["costumes"] = [costume(files[0][0], "backdrop", 240, 180)]
    project["targets"][1]["costumes"] = [costume(files[1][0], "Avery", 48, 70)]
    project["targets"][2]["costumes"] = [costume(files[2][0], "dem", 50, 35)]
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "project.json",
            json.dumps(project, ensure_ascii=False, separators=(",", ":")),
        )
        for name, data in files:
            z.writestr(name, data)
    # validate chain
    avery = project["targets"][1]["blocks"]
    flag = next(k for k, v in avery.items() if v["opcode"] == "event_whenflagclicked")
    assert avery[flag]["next"]
    assert any(v["opcode"] == "control_repeat_until" for v in avery.values())
    assert any(v["opcode"] == "event_whenkeypressed" for v in avery.values())
    print("Created", OUTPUT)


if __name__ == "__main__":
    main()
