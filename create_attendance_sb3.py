#!/usr/bin/env python3
"""Sequential attendance: Trang 5s -> Tho 5s -> ran 5s."""

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
EMPTY = "0"


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


def pred_is(b: B, name: str, parent: str) -> str:
    """Use both prediction is + model prediction = name."""
    or_id = b.add("operator_or", parent=parent, prefix="or")
    match = b.add(
        "teachableMachine_modelMatches",
        parent=or_id,
        fields={"CLASS_NAME": [name, None]},
        prefix="pm",
    )
    eq = b.add("operator_equals", parent=or_id, prefix="eq")
    pred = b.add("teachableMachine_modelPrediction", parent=eq, prefix="pred")
    b.blocks[eq]["inputs"] = {"OPERAND1": [2, pred], "OPERAND2": b.text(name)}
    b.blocks[or_id]["inputs"] = {"OPERAND1": [2, match], "OPERAND2": [2, eq]}
    return or_id


def build_turn(b: B, member: str, index: int, parent: str) -> tuple[str, str]:
    """One person turn: announce, countdown 5s while detecting, then next."""
    set_who = b.add(
        "data_setvariableto",
        parent=parent,
        fields={"VARIABLE": ["luot", "luot_var"]},
        inputs={"VALUE": b.text(member)},
        prefix=f"who{index}",
    )
    set_time = b.add(
        "data_setvariableto",
        parent=set_who,
        fields={"VARIABLE": ["time", "time_var"]},
        inputs={"VALUE": b.num(SECONDS)},
        prefix=f"t{index}",
    )
    say_turn = b.add(
        "looks_sayforsecs",
        parent=set_time,
        inputs={
            "MESSAGE": b.text(f"Luot {member}: nhin camera 5 giay!"),
            "SECS": b.num(2),
        },
        prefix=f"say{index}",
    )

    loop = b.add("control_repeat_until", parent=say_turn, prefix=f"loop{index}")
    # stop when time=0 OR already marked
    marked = b.add("operator_equals", parent=loop, prefix=f"mk{index}")
    item_m = b.add(
        "data_itemoflist",
        parent=marked,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix=f"itm{index}",
    )
    b.blocks[item_m]["inputs"] = {"INDEX": b.num(index)}
    b.blocks[marked]["inputs"] = {
        "OPERAND1": [2, item_m],
        "OPERAND2": b.text(member),
    }
    time0 = b.add("operator_equals", parent=loop, prefix=f"t0{index}")
    tvar = b.add(
        "data_variable",
        parent=time0,
        fields={"VARIABLE": ["time", "time_var"]},
        prefix=f"tv{index}",
    )
    b.blocks[time0]["inputs"] = {"OPERAND1": [2, tvar], "OPERAND2": b.num(0)}
    stop = b.add("operator_or", parent=loop, prefix=f"stop{index}")
    b.blocks[stop]["inputs"] = {"OPERAND1": [2, marked], "OPERAND2": [2, time0]}

    # inside loop: if prediction matches and slot empty -> mark
    if_pred = b.add("control_if", parent=loop, prefix=f"ip{index}")
    cond = pred_is(b, member, if_pred)
    if_empty = b.add("control_if", parent=if_pred, prefix=f"ie{index}")
    empty = b.add("operator_equals", parent=if_empty, prefix=f"ee{index}")
    item = b.add(
        "data_itemoflist",
        parent=empty,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix=f"it{index}",
    )
    b.blocks[item]["inputs"] = {"INDEX": b.num(index)}
    b.blocks[empty]["inputs"] = {
        "OPERAND1": [2, item],
        "OPERAND2": b.text(EMPTY),
    }
    replace = b.add(
        "data_replaceitemoflist",
        parent=if_empty,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix=f"rp{index}",
    )
    b.blocks[replace]["inputs"] = {
        "INDEX": b.num(index),
        "ITEM": b.text(member),
    }
    hello = b.add(
        "looks_say",
        parent=replace,
        inputs={"MESSAGE": b.text(f"Xin chao {member}! Da cham cong.")},
        prefix=f"hi{index}",
    )
    b.chain(replace, hello)
    b.blocks[if_empty]["inputs"] = {
        "CONDITION": [2, empty],
        "SUBSTACK": [2, replace],
    }
    b.blocks[if_pred]["inputs"] = {
        "CONDITION": [2, cond],
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
        "CONDITION": [2, stop],
        "SUBSTACK": [2, if_pred],
    }

    # if still empty after turn -> say missed (but continue)
    miss_if = b.add("control_if", parent=loop, prefix=f"miss{index}")
    still = b.add("operator_equals", parent=miss_if, prefix=f"st{index}")
    item2 = b.add(
        "data_itemoflist",
        parent=still,
        fields={"LIST": [LIST_NAME, LIST_ID]},
        prefix=f"it2{index}",
    )
    b.blocks[item2]["inputs"] = {"INDEX": b.num(index)}
    b.blocks[still]["inputs"] = {
        "OPERAND1": [2, item2],
        "OPERAND2": b.text(EMPTY),
    }
    say_miss = b.add(
        "looks_sayforsecs",
        parent=miss_if,
        inputs={
            "MESSAGE": b.text(f"Khong nhan ra {member}. Sang luot sau."),
            "SECS": b.num(2),
        },
        prefix=f"sm{index}",
    )
    b.blocks[miss_if]["inputs"] = {
        "CONDITION": [2, still],
        "SUBSTACK": [2, say_miss],
    }

    b.chain(set_who, set_time, say_turn, loop, miss_if)
    return set_who, miss_if


def build() -> dict:
    b = B()
    flag = b.add("event_whenflagclicked", top=True, x=30, y=30, prefix="flag")

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
            inputs={"ITEM": b.text(EMPTY)},
            prefix=f"z{i}",
        )
        zeros.append(z)
        prev = z

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
    intro = b.add(
        "looks_sayforsecs",
        parent=load,
        inputs={
            "MESSAGE": b.text("Bat dau cham cong lan luot tung nguoi"),
            "SECS": b.num(2),
        },
        prefix="intro",
    )

    turns = []
    parent = intro
    for index, member in enumerate(MEMBERS, start=1):
        first, last = build_turn(b, member, index, parent)
        turns.append((first, last))
        parent = last

    # link turns
    for i in range(len(turns) - 1):
        b.chain(turns[i][1], turns[i + 1][0])

    # final report
    final_parent = turns[-1][1]
    if_full = b.add("control_if_else", parent=final_parent, prefix="full")
    eqs = []
    for index, member in enumerate(MEMBERS, start=1):
        eq = b.add("operator_equals", parent=if_full, prefix=f"fe{index}")
        item = b.add(
            "data_itemoflist",
            parent=eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"fi{index}",
        )
        b.blocks[item]["inputs"] = {"INDEX": b.num(index)}
        b.blocks[eq]["inputs"] = {
            "OPERAND1": [2, item],
            "OPERAND2": b.text(member),
        }
        eqs.append(eq)
    and1 = b.add("operator_and", parent=if_full, prefix="a1")
    b.blocks[and1]["inputs"] = {"OPERAND1": [2, eqs[0]], "OPERAND2": [2, eqs[1]]}
    and2 = b.add("operator_and", parent=if_full, prefix="a2")
    b.blocks[and2]["inputs"] = {"OPERAND1": [2, and1], "OPERAND2": [2, eqs[2]]}
    b.blocks[eqs[0]]["parent"] = and1
    b.blocks[eqs[1]]["parent"] = and1
    b.blocks[and1]["parent"] = and2
    b.blocks[eqs[2]]["parent"] = and2

    say_full = b.add(
        "looks_sayforsecs",
        parent=if_full,
        inputs={"MESSAGE": b.text("Moi nguoi da den day du"), "SECS": b.num(3)},
        prefix="sayfull",
    )

    misses = []
    for index, member in enumerate(MEMBERS, start=1):
        parent_m = misses[-1] if misses else if_full
        if_m = b.add("control_if", parent=parent_m, prefix=f"m{index}")
        eq = b.add("operator_equals", parent=if_m, prefix=f"me{index}")
        item = b.add(
            "data_itemoflist",
            parent=eq,
            fields={"LIST": [LIST_NAME, LIST_ID]},
            prefix=f"mi{index}",
        )
        b.blocks[item]["inputs"] = {"INDEX": b.num(index)}
        b.blocks[eq]["inputs"] = {
            "OPERAND1": [2, item],
            "OPERAND2": b.text(EMPTY),
        }
        say_m = b.add(
            "looks_sayforsecs",
            parent=if_m,
            inputs={"MESSAGE": b.text(f"Vang {member}"), "SECS": b.num(2)},
            prefix=f"sm{index}",
        )
        b.blocks[if_m]["inputs"] = {"CONDITION": [2, eq], "SUBSTACK": [2, say_m]}
        misses.append(if_m)
    b.chain(*misses)
    b.blocks[if_full]["inputs"] = {
        "CONDITION": [2, and2],
        "SUBSTACK": [2, say_full],
        "SUBSTACK2": [2, misses[0]],
    }

    b.chain(flag, clear, *zeros, use, von, trans, load, intro)
    b.chain(intro, turns[0][0])
    b.chain(turns[-1][1], if_full)

    comments = {
        "c1": {
            "blockId": use,
            "x": 400,
            "y": 40,
            "width": 240,
            "height": 90,
            "minimized": False,
            "text": "Lan luot: Trang 5s -> Tho 5s -> ran 5s. Bam co xanh.",
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
                "value": [EMPTY, EMPTY, EMPTY],
                "width": 0,
                "height": 0,
                "x": 260,
                "y": 20,
                "visible": True,
            },
        ],
        "extensions": ["teachableMachine"],
        "meta": {"semver": "3.0.0", "vm": "11.1.0", "agent": "sequential-5s"},
        "_assets": [stage_f, sprite_f],
    }


def main() -> None:
    project = build()
    assets = project.pop("_assets")
    blocks = project["targets"][1]["blocks"]
    assert sum(1 for v in blocks.values() if v["opcode"] == "control_repeat_until") == 3
    # verify chain includes all 3 loops
    flag = next(k for k, v in blocks.items() if v["opcode"] == "event_whenflagclicked")
    cur, ops = flag, []
    while cur:
        ops.append(blocks[cur]["opcode"])
        cur = blocks[cur].get("next")
    assert ops.count("control_repeat_until") == 3, ops
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
