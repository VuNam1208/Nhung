#!/usr/bin/env python3
"""Scratch 3 - Tro choi ghep noi (English <-> Vietnamese)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

OUTPUT = Path(__file__).with_name("tro-choi-ghep-noi.sb3")

PAIRS_L1 = (
    ("Apple", "Tao"),
    ("Cat", "Meo"),
    ("Book", "Sach"),
    ("Sun", "Mat troi"),
    ("Water", "Nuoc"),
)
PAIRS_L2 = (
    ("Elephant", "Voi"),
    ("Computer", "May tinh"),
    ("School", "Truong hoc"),
    ("Friend", "Ban be"),
    ("Happy", "Vui ve"),
)

MSG = {
    "datLai": "datLai",
    "batDau": "batDau",
    "batCap1": "batCap1",
    "batCap2": "batCap2",
    "thang": "thangCuoc",
    "ghepDung": "ghepDung",
    "ghepSai": "ghepSai",
    "xongCap1": "xongCap1",
}


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
        i = self.nid(prefix)
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
            blk["x"], blk["y"] = x, y
        self.blocks[i] = blk
        return i

    def chain(self, *ids: str) -> None:
        for a, c in zip(ids, ids[1:]):
            self.blocks[a]["next"] = c
            self.blocks[c]["parent"] = a

    def num(self, v: int | float) -> list:
        return [1, [4, str(v)]]

    def txt(self, v: str) -> list:
        return [1, [10, v]]

    def var(self, name: str, vid: str, parent: str | None = None) -> str:
        return self.add(
            "data_variable",
            parent=parent,
            fields={"VARIABLE": [name, vid]},
            prefix="vr",
        )

    def set_var(self, name: str, vid: str, val, parent: str | None = None) -> str:
        v = self.num(val) if isinstance(val, (int, float)) else self.txt(val)
        return self.add(
            "data_setvariableto",
            parent=parent,
            fields={"VARIABLE": [name, vid]},
            inputs={"VALUE": v},
            prefix="sv",
        )

    def eq_var(self, name: str, vid: str, val, parent: str | None = None) -> str:
        eq = self.add("operator_equals", parent=parent, prefix="eq")
        ref = self.var(name, vid, eq)
        rhs = self.num(val) if isinstance(val, (int, float)) else self.txt(val)
        self.blocks[eq]["inputs"] = {"OPERAND1": [2, ref], "OPERAND2": rhs}
        return eq

    def on_msg(self, msg: str, x: int, y: int) -> str:
        h = self.add("event_whenbroadcastreceived", top=True, x=x, y=y, prefix="wm")
        self.blocks[h]["fields"] = {"BROADCAST_OPTION": [msg, MSG[msg]]}
        return h

    def broadcast(self, msg: str, parent: str | None = None) -> str:
        return self.add(
            "event_broadcast",
            parent=parent,
            fields={"BROADCAST_OPTION": [msg, MSG[msg]]},
            prefix="bc",
        )

    def custom_def(self, proccode: str, procid: str, x: int, y: int) -> str:
        d = self.add("procedures_definition", top=True, x=x, y=y, prefix="pd")
        mut = {
            "tagName": "mutation",
            "proccode": proccode,
            "procid": procid,
            "argumentids": "[]",
            "argumentnames": "[]",
            "argumentdefaults": "[]",
            "warp": False,
        }
        self.blocks[d]["mutation"] = mut
        p = self.add("procedures_prototype", parent=d, shadow=True, prefix="pp")
        self.blocks[p]["mutation"] = dict(mut)
        self.blocks[d]["inputs"] = {"custom_block": [1, p]}
        return d

    def custom_call(self, proccode: str, procid: str, parent: str | None = None) -> str:
        c = self.add("procedures_call", parent=parent, prefix="pc")
        self.blocks[c]["mutation"] = {
            "tagName": "mutation",
            "proccode": proccode,
            "procid": procid,
            "argumentids": "[]",
            "argumentnames": "[]",
            "argumentdefaults": "[]",
            "warp": False,
        }
        return c


def md5_asset(data: bytes, ext: str) -> tuple[str, bytes]:
    h = hashlib.md5(data).hexdigest()
    return f"{h}.{ext}", data


def card_svg(text: str, color: str) -> bytes:
    t = text.replace("&", "&amp;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="120" height="64">
<rect width="120" height="64" rx="10" fill="{color}" stroke="#2c3e50" stroke-width="2"/>
<text x="60" y="38" text-anchor="middle" font-family="Arial" font-size="13" fill="#fff">{t}</text>
</svg>""".encode()


def backdrop_svg(title: str, sub: str, bg: str) -> bytes:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">
<rect width="480" height="360" fill="{bg}"/>
<text x="240" y="70" font-family="Arial" font-size="26" fill="#2c3e50" text-anchor="middle">{title}</text>
<text x="240" y="110" font-family="Arial" font-size="15" fill="#34495e" text-anchor="middle">{sub}</text>
</svg>""".encode()


def btn_svg(text: str) -> bytes:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="130" height="46">
<rect width="130" height="46" rx="8" fill="#27ae60"/>
<text x="65" y="30" text-anchor="middle" font-family="Arial" font-size="15" fill="#fff">{text}</text>
</svg>""".encode()


def costume(fn: str, name: str, cx: int, cy: int) -> dict:
    return {
        "assetId": fn.split(".")[0],
        "name": name,
        "bitmapResolution": 1,
        "md5ext": fn,
        "dataFormat": "svg",
        "rotationCenterX": cx,
        "rotationCenterY": cy,
    }


def build_card(
    name: str,
    partner: str,
    label: str,
    color: str,
    x: int,
    y: int,
    layer: int,
    speed_slow: int,
    speed_fast: int,
) -> tuple[dict, tuple[str, bytes]]:
    b = B()
    fn, svg = md5_asset(card_svg(label, color), "svg")

    # reset hide
    f = b.add("event_whenflagclicked", top=True, x=20, y=20, prefix="f")
    b.chain(f, b.add("looks_hide", prefix="h"), b.set_var("daGhep", "v_paired", 0))

    # show level 1
    h1 = b.on_msg("batCap1", 20, 120)
    b.chain(
        h1,
        b.add("looks_show", prefix="s1"),
        b.add("motion_gotoxy", prefix="g1", inputs={"X": b.num(x), "Y": b.num(y)}),
        b.set_var("daGhep", "v_paired", 0),
        b.set_var("dangKeo", "v_drag", 0),
        b.set_var("tocDo", "v_speed", speed_slow),
    )

    # show level 2 (same sprite, new positions/speed)
    h2 = b.on_msg("batCap2", 20, 220)
    b.chain(
        h2,
        b.add("looks_show", prefix="s2"),
        b.add("motion_gotoxy", prefix="g2", inputs={"X": b.num(x), "Y": b.num(y)}),
        b.set_var("daGhep", "v_paired", 0),
        b.set_var("dangKeo", "v_drag", 0),
        b.set_var("tocDo", "v_speed", speed_fast),
    )

    # random move when free
    fr = b.add("event_whenflagclicked", top=True, x=200, y=20, prefix="fr")
    lp = b.add("control_forever", prefix="lp")
    ok = b.eq_var("daGhep", "v_paired", 0, lp)
    ok2 = b.eq_var("dangKeo", "v_drag", 0, lp)
    both = b.add("operator_and", parent=lp, prefix="and")
    b.blocks[both]["inputs"] = {"OPERAND1": [2, ok], "OPERAND2": [2, ok2]}
    inner = b.add("control_if", parent=lp, prefix="ifi")
    b.blocks[inner]["inputs"] = {"CONDITION": [2, both], "SUBSTACK": [2, None]}
    tr = b.add("motion_turnright", parent=inner, prefix="tr", inputs={"DEGREES": b.num(20)})
    mv = b.add("motion_movesteps", parent=tr, prefix="mv")
    spd = b.var("tocDo", "v_speed", mv)
    b.blocks[mv]["inputs"] = {"STEPS": [2, spd]}
    bn = b.add("motion_ifonedgebounce", parent=mv, prefix="bn")
    b.blocks[inner]["inputs"]["SUBSTACK"] = [2, tr]
    b.blocks[tr]["parent"] = inner
    b.blocks[lp]["inputs"] = {"SUBSTACK": [2, inner]}
    b.blocks[inner]["parent"] = lp
    b.chain(fr, lp)

    # follow partner when paired
    fr2 = b.add("event_whenflagclicked", top=True, x=200, y=120, prefix="fr2")
    lp2 = b.add("control_forever", prefix="lp2")
    ifp = b.add("control_if", prefix="ifp")
    p1 = b.eq_var("daGhep", "v_paired", 1, ifp)
    p2 = b.eq_var("vaiTro", "v_role", "theo", ifp)
    ba = b.add("operator_and", prefix="ba")
    b.blocks[ba]["inputs"] = {"OPERAND1": [2, p1], "OPERAND2": [2, p2]}
    gt = b.add("motion_gotoxy", prefix="gt")
    sx = b.add(
        "sensing_of",
        parent=gt,
        prefix="sx",
        fields={"PROPERTY": ["x position", None], "OBJECT": [partner, None]},
    )
    sy = b.add(
        "sensing_of",
        parent=gt,
        prefix="sy",
        fields={"PROPERTY": ["y position", None], "OBJECT": [partner, None]},
    )
    ox = b.add("operator_add", parent=gt, prefix="ox")
    b.blocks[ox]["inputs"] = {"NUM1": [2, sx], "NUM2": b.num(65)}
    b.blocks[gt]["inputs"] = {"X": [3, ox, b.num(0)], "Y": [2, sy]}
    b.blocks[ifp]["inputs"] = {"CONDITION": [2, ba], "SUBSTACK": [2, gt]}
    b.blocks[gt]["parent"] = ifp
    b.blocks[lp2]["inputs"] = {"SUBSTACK": [2, ifp]}
    b.blocks[ifp]["parent"] = lp2
    b.chain(fr2, lp2)

    # drag + match
    ck = b.add("event_whenthisspriteclicked", top=True, x=360, y=20, prefix="ck")
    if0 = b.add("control_if", prefix="if0")
    b.blocks[if0]["inputs"] = {
        "CONDITION": [2, b.eq_var("daGhep", "v_paired", 0, if0)],
        "SUBSTACK": [2, None],
    }
    d1 = b.set_var("dangKeo", "v_drag", 1)
    b.blocks[if0]["inputs"]["SUBSTACK"] = [2, d1]
    gf = b.add("motion_gotofront", parent=d1, prefix="gf")
    rp = b.add("control_repeat_until", parent=gf, prefix="rp")
    md = b.add("sensing_mousedown", parent=rp, prefix="md")
    b.blocks[rp]["inputs"] = {"CONDITION": [2, md], "SUBSTACK": [2, None]}
    gm = b.add("motion_gotoxy", parent=rp, prefix="gm")
    mx = b.add("sensing_mousex", parent=gm, prefix="mx")
    my = b.add("sensing_mousey", parent=gm, prefix="my")
    b.blocks[gm]["inputs"] = {"X": [2, mx], "Y": [2, my]}
    b.blocks[rp]["inputs"]["SUBSTACK"] = [2, gm]
    b.blocks[gm]["parent"] = rp
    d0 = b.set_var("dangKeo", "v_drag", 0, rp)
    b.chain(d1, gf, rp, d0)

    ift = b.add("control_if", parent=d0, prefix="ift")
    tc = b.add(
        "sensing_touchingobject",
        prefix="tc",
        fields={"TOUCHINGOBJECTMENU": [partner, None]},
    )
    b.blocks[ift]["inputs"] = {"CONDITION": [2, tc], "SUBSTACK": [2, None]}
    sp1 = b.set_var("daGhep", "v_paired", 1)
    sr = b.set_var("vaiTro", "v_role", "lanh dao")
    b.chain(sp1, sr)
    say = b.add(
        "looks_sayforsecs",
        parent=sr,
        inputs={"MESSAGE": b.txt("Dung roi!"), "SECS": b.num(1)},
    )
    bc = b.broadcast("ghepDung", say)
    ch = b.add(
        "data_changevariableby",
        parent=bc,
        fields={"VARIABLE": ["soCapDaGhep", "g_matched"]},
        inputs={"VALUE": b.num(1)},
    )
    b.blocks[ift]["inputs"]["SUBSTACK"] = [2, sp1]
    b.blocks[sp1]["parent"] = ift
    b.chain(d0, ift)

    ife = b.add("control_if", parent=ift, prefix="ife")
    tc2 = b.add(
        "sensing_touchingobject",
        prefix="tc2",
        fields={"TOUCHINGOBJECTMENU": ["_edge_", None]},
    )
    nt = b.add("operator_not", prefix="nt")
    b.blocks[nt]["inputs"] = {"OPERAND": [2, tc2]}
    b.blocks[ife]["inputs"] = {"CONDITION": [2, nt], "SUBSTACK": [2, None]}
    wrong = b.custom_call("phat hieu ung sai", "proc_wrong", ife)
    b.blocks[ife]["inputs"]["SUBSTACK"] = [2, wrong]

    wd = b.custom_def("phat hieu ung sai", "proc_wrong", 520, 20)
    sb = b.add(
        "looks_sayforsecs",
        parent=wd,
        prefix="sb",
        inputs={"MESSAGE": b.txt("Chua dung!"), "SECS": b.num(1)},
    )
    fx = b.add(
        "looks_changeeffectby",
        parent=sb,
        prefix="fx",
        fields={"EFFECT": ["color", None]},
        inputs={"CHANGE": b.num(30)},
    )
    bbc = b.broadcast("ghepSai", fx)
    b.chain(wd, sb, fx, bbc)
    b.chain(ift, ife)
    b.chain(ck, if0)

    # on partner paired -> become follower
    og = b.on_msg("ghepDung", 360, 120)
    ifg = b.add("control_if", prefix="ifg")
    tc3 = b.add(
        "sensing_touchingobject",
        prefix="tc3",
        fields={"TOUCHINGOBJECTMENU": [partner, None]},
    )
    p0 = b.eq_var("daGhep", "v_paired", 0, ifg)
    both2 = b.add("operator_and", prefix="b2")
    b.blocks[both2]["inputs"] = {"OPERAND1": [2, tc3], "OPERAND2": [2, p0]}
    b.blocks[ifg]["inputs"] = {"CONDITION": [2, both2], "SUBSTACK": [2, None]}
    sp2 = b.set_var("daGhep", "v_paired", 1)
    sr2 = b.set_var("vaiTro", "v_role", "theo")
    b.blocks[ifg]["inputs"]["SUBSTACK"] = [2, sp2]
    b.chain(sp2, sr2)
    b.chain(og, ifg)

    sprite = {
        "isStage": False,
        "name": name,
        "variables": {
            "v_paired": ["daGhep", 0],
            "v_drag": ["dangKeo", 0],
            "v_role": ["vaiTro", "doc lap"],
            "v_speed": ["tocDo", 4],
        },
        "lists": {},
        "broadcasts": {},
        "blocks": b.blocks,
        "comments": {},
        "currentCostume": 0,
        "costumes": [costume(fn, label, 60, 32)],
        "sounds": [],
        "volume": 100,
        "layerOrder": layer,
        "visible": True,
        "x": x,
        "y": y,
        "size": 95,
        "direction": 90,
        "draggable": False,
        "rotationStyle": "all around",
    }
    return sprite, (fn, svg)


def add_hide_on(b: B, msg: str, x: int, y: int) -> None:
    h = b.on_msg(msg, x, y)
    b.chain(h, b.add("looks_hide", prefix="hd"))


def add_show_on(b: B, msg: str, x: int, y: int) -> None:
    h = b.on_msg(msg, x, y)
    b.chain(h, b.add("looks_show", prefix="sh"))


def build_button(name: str, label: str, msg: str, x: int, y: int, layer: int) -> tuple[dict, tuple[str, bytes]]:
    b = B()
    fn, svg = md5_asset(btn_svg(label), "svg")
    c = b.add("event_whenthisspriteclicked", top=True, x=40, y=40, prefix="c")
    b.chain(c, b.broadcast(msg))
    add_hide_on(b, "batCap1", 200, 40)
    add_show_on(b, "datLai", 200, 120)
    if name == "BtnCapTiep":
        add_hide_on(b, "datLai", 360, 40)
        add_hide_on(b, "batCap1", 360, 120)
        add_show_on(b, "xongCap1", 360, 200)
        add_hide_on(b, "batCap2", 360, 280)
        add_hide_on(b, "thang", 360, 360)
    return (
        {
            "isStage": False,
            "name": name,
            "variables": {},
            "lists": {},
            "broadcasts": {},
            "blocks": b.blocks,
            "comments": {},
            "currentCostume": 0,
            "costumes": [costume(fn, label, 65, 23)],
            "sounds": [],
            "volume": 100,
            "layerOrder": layer,
            "visible": True,
            "x": x,
            "y": y,
            "size": 100,
            "direction": 90,
            "draggable": False,
            "rotationStyle": "all around",
        },
        (fn, svg),
    )


def build_stage(assets: list[tuple[str, bytes]]) -> dict:
    b = B()
    f = b.add("event_whenflagclicked", top=True, x=20, y=20, prefix="f")
    b.chain(f, b.broadcast("datLai"))

    r = b.on_msg("datLai", 20, 120)
    sw = b.add("looks_switchbackdropto", prefix="sw")
    b.blocks[sw]["fields"] = {"BACKDROP": ["Mo dau", "bd_intro"]}
    b.chain(
        r,
        sw,
        b.set_var("soCapDaGhep", "g_matched", 0),
        b.set_var("capDo", "g_level", 0),
    )

    s = b.on_msg("batDau", 200, 120)
    sw1 = b.add("looks_switchbackdropto", prefix="sw1")
    b.blocks[sw1]["fields"] = {"BACKDROP": ["Cap 1", "bd_l1"]}
    b.chain(
        s,
        sw1,
        b.set_var("capDo", "g_level", 1),
        b.set_var("soCapDaGhep", "g_matched", 0),
        b.broadcast("batCap1"),
    )

    m1 = b.on_msg("batCap1", 360, 120)
    fr = b.add("control_forever", prefix="fr")
    if5 = b.add("control_if", prefix="if5")
    eq = b.add("operator_equals", prefix="eq")
    rv = b.var("soCapDaGhep", "g_matched", eq)
    b.blocks[eq]["inputs"] = {"OPERAND1": [2, rv], "OPERAND2": b.num(5)}
    lv = b.eq_var("capDo", "g_level", 1, if5)
    done1 = b.add("operator_and", prefix="done1")
    b.blocks[done1]["inputs"] = {"OPERAND1": [2, eq], "OPERAND2": [2, lv]}
    w = b.add("control_wait", prefix="w", inputs={"DURATION": b.num(0.1)})
    bdone = b.broadcast("xongCap1", w)
    b.blocks[if5]["inputs"] = {"CONDITION": [2, done1], "SUBSTACK": [2, w]}
    b.blocks[fr]["inputs"] = {"SUBSTACK": [2, if5]}
    b.blocks[if5]["parent"] = fr
    b.chain(m1, fr)

    x1 = b.on_msg("xongCap1", 20, 260)
    b.chain(
        x1,
        b.add(
            "looks_sayforsecs",
            prefix="sx",
            inputs={"MESSAGE": b.txt("Cap 1 xong! Bam Cap tiep"), "SECS": b.num(2)},
        ),
    )

    l2 = b.on_msg("batCap2", 200, 260)
    sw2 = b.add("looks_switchbackdropto", prefix="sw2")
    b.blocks[sw2]["fields"] = {"BACKDROP": ["Cap 2", "bd_l2"]}
    b.chain(
        l2,
        sw2,
        b.set_var("capDo", "g_level", 2),
        b.set_var("soCapDaGhep", "g_matched", 0),
    )

    m2 = b.on_msg("batCap2", 360, 260)
    fr2 = b.add("control_forever", prefix="fr2")
    if2 = b.add("control_if", prefix="if2")
    eq2 = b.add("operator_equals", prefix="eq2")
    rv2 = b.var("soCapDaGhep", "g_matched", eq2)
    b.blocks[eq2]["inputs"] = {"OPERAND1": [2, rv2], "OPERAND2": b.num(5)}
    lv2 = b.eq_var("capDo", "g_level", 2, if2)
    done2 = b.add("operator_and", prefix="done2")
    b.blocks[done2]["inputs"] = {"OPERAND1": [2, eq2], "OPERAND2": [2, lv2]}
    w2 = b.add("control_wait", prefix="w2", inputs={"DURATION": b.num(0.1)})
    win = b.broadcast("thang", w2)
    b.blocks[if2]["inputs"] = {"CONDITION": [2, done2], "SUBSTACK": [2, w2]}
    b.blocks[fr2]["inputs"] = {"SUBSTACK": [2, if2]}
    b.blocks[if2]["parent"] = fr2
    b.chain(m2, fr2)

    wt = b.on_msg("thang", 20, 400)
    sw3 = b.add("looks_switchbackdropto", prefix="sw3")
    b.blocks[sw3]["fields"] = {"BACKDROP": ["Ket thuc", "bd_win"]}
    b.chain(
        wt,
        sw3,
        b.add(
            "looks_sayforsecs",
            prefix="win",
            inputs={"MESSAGE": b.txt("Chuc mung! Hoan thanh!"), "SECS": b.num(3)},
        ),
    )

    bds = [
        ("Mo dau", "bd_intro", backdrop_svg("TRO CHOI GHEP NOI", "Keo tu Anh sang nghia Viet", "#ecf0f1")),
        ("Cap 1", "bd_l1", backdrop_svg("CAP 1 - 5 cap tu", "Toc do cham", "#d5f5e3")),
        ("Cap 2", "bd_l2", backdrop_svg("CAP 2 - 5 cap tu", "Toc do nhanh hon", "#fdebd0")),
        ("Ket thuc", "bd_win", backdrop_svg("CHUC MUNG!", "Ban da thang cuoc", "#fadbd8")),
    ]
    costumes = []
    for disp, _, svg in bds:
        fn, data = md5_asset(svg, "svg")
        assets.append((fn, data))
        costumes.append(
            {
                "name": disp,
                "assetId": fn.split(".")[0],
                "md5ext": fn,
                "dataFormat": "svg",
                "rotationCenterX": 240,
                "rotationCenterY": 180,
            }
        )

    return {
        "isStage": True,
        "name": "Stage",
        "variables": {"g_matched": ["soCapDaGhep", 0], "g_level": ["capDo", 0]},
        "lists": {
            "list_l1": ["danhSachCap1", [f"{a}-{b}" for a, b in PAIRS_L1]],
            "list_l2": ["danhSachCap2", [f"{a}-{b}" for a, b in PAIRS_L2]],
        },
        "broadcasts": MSG,
        "blocks": b.blocks,
        "comments": {
            "n1": {
                "blockId": f,
                "x": 420,
                "y": 20,
                "width": 180,
                "height": 80,
                "minimized": False,
                "text": "Bien: soCapDaGhep, capDo\nDanh sach cap tu cap 1/2",
            }
        },
        "currentCostume": 0,
        "costumes": costumes,
        "sounds": [],
        "volume": 100,
        "layerOrder": 0,
        "tempo": 60,
        "videoTransparency": 50,
        "videoState": "off",
        "textToSpeechLanguage": None,
    }


def build_project() -> tuple[dict, list[tuple[str, bytes]]]:
    assets: list[tuple[str, bytes]] = []
    stage = build_stage(assets)
    targets = [stage]
    layer = 1

    btn1, a1 = build_button("BtnBatDau", "Bat dau", "batDau", 0, -130, layer)
    assets.append(a1)
    targets.append(btn1)
    layer += 1

    btn2, a2 = build_button("BtnCapTiep", "Cap tiep", "batCap2", 0, -130, layer)
    assets.append(a2)
    targets.append(btn2)
    layer += 1

    colors = ["#e74c3c", "#3498db", "#9b59b6", "#f1c40f", "#1abc9c"]
    pos_en = [(-170, 90), (-50, 30), (70, 90), (170, 30), (-100, -50)]
    pos_vi = [(-170, -50), (-50, -110), (70, -50), (170, -110), (100, 50)]

    for i, ((en, vi), col) in enumerate(zip(PAIRS_L1, colors)):
        en_name, vi_name = f"EN{i+1}", f"VI{i+1}"
        en, ae = build_card(en_name, vi_name, en, col, pos_en[i][0], pos_en[i][1], layer, 4, 8)
        vi, av = build_card(vi_name, en_name, vi, col, pos_vi[i][0], pos_vi[i][1], layer + 1, 4, 8)
        assets.extend([ae, av])
        targets.extend([en, vi])
        layer += 2

    # Level 2 labels on same sprites - update via say on batCap2 (costumes stay, labels in name)
    # Rebuild with L2 text on batCap2 by extra sprites would duplicate; use same 5 pairs
    # Different words for L2 - add EN6-10 / VI6-10 hidden on L1, shown on L2
    colors2 = ["#e67e22", "#2980b9", "#8e44ad", "#27ae60", "#d35400"]
    for i, ((en, vi), col) in enumerate(zip(PAIRS_L2, colors2)):
        en_name, vi_name = f"E2_{i+1}", f"V2_{i+1}"
        en, ae = build_card(en_name, vi_name, en, col, pos_en[i][0], pos_en[i][1], layer, 5, 10)
        vi, av = build_card(vi_name, en_name, vi, col, pos_vi[i][0], pos_vi[i][1], layer + 1, 5, 10)
        assets.extend([ae, av])
        targets.extend([en, vi])
        layer += 2

    for t in targets:
        nm = t.get("name", "")
        patch = B()
        if nm.startswith(("EN", "VI")) and not nm.startswith(("E2", "V2")):
            add_hide_on(patch, "batCap2", 0, 0)
            add_show_on(patch, "batCap1", 100, 0)
            add_hide_on(patch, "datLai", 200, 0)
        if nm.startswith(("E2_", "V2_")):
            add_hide_on(patch, "batCap1", 0, 0)
            add_hide_on(patch, "datLai", 100, 0)
            add_show_on(patch, "batCap2", 200, 0)
        if patch.blocks:
            t["blocks"].update(patch.blocks)

    project = {
        "targets": targets,
        "monitors": [
            {
                "id": "g_matched",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "soCapDaGhep"},
                "spriteName": None,
                "value": 0,
                "width": 0,
                "height": 0,
                "x": 5,
                "y": 5,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 5,
                "isDiscrete": True,
            }
        ],
        "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "11.2.0", "agent": "ghep-noi-v2"},
    }
    return project, assets


def main() -> None:
    project, assets = build_project()
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(project, ensure_ascii=False, separators=(",", ":")))
        for n, d in assets:
            z.writestr(n, d)
    print(f"OK: {OUTPUT}  sprites={len(project['targets'])}  assets={len(assets)}")


if __name__ == "__main__":
    main()
