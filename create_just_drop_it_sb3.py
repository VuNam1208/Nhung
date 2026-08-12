#!/usr/bin/env python3
"""Scratch 3 - Just Drop It / Tay gap ky dieu (claw machine underwater)."""

from __future__ import annotations

import hashlib
import json
import secrets
import zipfile
from pathlib import Path

OUTPUT = Path(__file__).with_name("just-drop-it-tay-gap.sb3")
POP_WAV = Path("/tmp/empty.sb3")

BROADCAST_LABELS = {
    "datLai": "datLai",
    "batDau": "batDau",
    "batChoi": "batChoi",
    "ketThuc": "ketThuc",
    "daGap": "daGap",
    "gapTruot": "gapTruot",
    "datVat": "datVat",
}
BROADCAST_IDS = {k: f"bcast{k[:6]}{i:02d}" for i, k in enumerate(BROADCAST_LABELS)}

ITEMS = (
    # name, label, color, points, x, y, moves
    ("Chai", "Chai +10", "#3498db", 10, -150, -120, False),
    ("Tui", "Tui +15", "#ecf0f1", 15, -60, -140, True),
    ("Ly", "Ly +5", "#2ecc71", 5, 40, -100, False),
    ("Sao", "Sao +20", "#e67e22", 20, 130, -130, True),
    ("Vo", "Vo +8", "#fd79a8", 8, -120, -60, False),
    ("Bom", "Bom -20", "#2d3436", -20, 80, -70, False),
    ("Ran", "Ran -15", "#636e72", -15, 160, -90, True),
)


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
        shadow: bool = False,
        top: bool = False,
        x: int = 0,
        y: int = 0,
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
            blk["x"], blk["y"] = x, y
        self.blocks[bid] = blk
        return bid

    def chain(self, *ids: str) -> None:
        for a, c in zip(ids, ids[1:]):
            self.blocks[a]["next"] = c
            self.blocks[c]["parent"] = a

    def attach(self, parent: str, name: str, child: str) -> None:
        self.blocks[parent]["inputs"][name] = [2, child]
        self.blocks[child]["parent"] = parent

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

    def change_var(self, name: str, vid: str, val: int | float, parent: str | None = None) -> str:
        return self.add(
            "data_changevariableby",
            parent=parent,
            fields={"VARIABLE": [name, vid]},
            inputs={"VALUE": self.num(val)},
            prefix="cv",
        )

    def eq_var(self, name: str, vid: str, val, parent: str | None = None) -> str:
        eq = self.add("operator_equals", parent=parent, prefix="eq")
        ref = self.var(name, vid, eq)
        rhs = self.num(val) if isinstance(val, (int, float)) else self.txt(val)
        self.blocks[eq]["inputs"] = {"OPERAND1": [2, ref], "OPERAND2": rhs}
        return eq

    def gt_var(self, name: str, vid: str, val: int | float, parent: str | None = None) -> str:
        gt = self.add("operator_gt", parent=parent, prefix="gt")
        ref = self.var(name, vid, gt)
        self.blocks[gt]["inputs"] = {"OPERAND1": [2, ref], "OPERAND2": self.num(val)}
        return gt

    def on_msg(self, key: str, x: int, y: int) -> str:
        h = self.add("event_whenbroadcastreceived", top=True, x=x, y=y, prefix="wm")
        self.blocks[h]["fields"] = {
            "BROADCAST_OPTION": [BROADCAST_LABELS[key], BROADCAST_IDS[key]]
        }
        return h

    def broadcast(self, key: str, parent: str | None = None) -> str:
        return self.add(
            "event_broadcast",
            parent=parent,
            fields={"BROADCAST_OPTION": [BROADCAST_LABELS[key], BROADCAST_IDS[key]]},
            prefix="bc",
        )

    def play_pop(self, parent: str | None = None) -> str:
        return self.add(
            "sound_play",
            parent=parent,
            fields={"SOUND_MENU": ["pop", "83a9787d4cb6f3b7632b4ddfebf74367"]},
            prefix="snd",
        )


def md5_asset(data: bytes, ext: str) -> tuple[str, bytes]:
    return f"{hashlib.md5(data).hexdigest()}.{ext}", data


def rect_svg(w: int, h: int, color: str, label: str = "", stroke: str = "#2c3e50") -> bytes:
    t = label.replace("&", "&amp;")
    mid = f'<text x="{w//2}" y="{h//2+5}" text-anchor="middle" font-family="Arial" font-size="11" fill="#fff">{t}</text>' if t else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
<rect width="{w}" height="{h}" rx="6" fill="{color}" stroke="{stroke}" stroke-width="2"/>{mid}
</svg>""".encode()


def backdrop_svg(title: str, sub: str, bg: str, extra: str = "") -> bytes:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">
<rect width="480" height="360" fill="{bg}"/>
<text x="240" y="55" font-family="Arial" font-size="24" fill="#fff" text-anchor="middle">{title}</text>
<text x="240" y="90" font-family="Arial" font-size="13" fill="#ecf0f1" text-anchor="middle">{sub}</text>
{extra}
</svg>""".encode()


def underwater_bg() -> bytes:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#74b9ff"/><stop offset="100%" stop-color="#0984e3"/></linearGradient></defs>
<rect width="480" height="360" fill="url(#g)"/>
<rect y="250" width="480" height="110" fill="#dfe6e9"/>
<ellipse cx="80" cy="280" rx="40" ry="15" fill="#b2bec3"/>
<ellipse cx="200" cy="300" rx="55" ry="18" fill="#b2bec3"/>
<ellipse cx="360" cy="285" rx="45" ry="16" fill="#b2bec3"/>
<path d="M30 250 Q50 200 70 250" stroke="#00b894" stroke-width="8" fill="none"/>
<path d="M400 250 Q420 190 440 250" stroke="#00b894" stroke-width="8" fill="none"/>
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


def sprite_base(name: str, sid: str, layer: int, x: int, y: int, size: int = 100) -> dict:
    return {
        "isStage": False,
        "name": name,
        "id": sid,
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [],
        "sounds": [],
        "volume": 100,
        "layerOrder": layer,
        "visible": True,
        "x": x,
        "y": y,
        "size": size,
        "direction": 90,
        "draggable": False,
        "rotationStyle": "all around",
    }


def add_hide_show(b: B, key: str, hide: bool, x: int, y: int) -> None:
    h = b.on_msg(key, x, y)
    b.chain(h, b.add("looks_hide" if hide else "looks_show", prefix="hs"))


def build_button(name: str, label: str, msg: str, x: int, y: int, layer: int, sid: str) -> tuple[dict, tuple[str, bytes]]:
    b = B()
    fn, svg = md5_asset(rect_svg(130, 46, "#27ae60", label), "svg")
    c = b.add("event_whenthisspriteclicked", top=True, x=40, y=40, prefix="c")
    b.chain(c, b.broadcast(msg))
    add_hide_show(b, "batChoi", True, 200, 40)
    add_hide_show(b, "datLai", False, 200, 120)
    if name == "BtnChoiLai":
        add_hide_show(b, "ketThuc", True, 360, 40)
        add_show_on = b.on_msg("ketThuc", 360, 120)
        b.chain(add_show_on, b.add("looks_show", prefix="sh"))
    sp = sprite_base(name, sid, layer, x, y, 100)
    sp["blocks"] = b.blocks
    sp["costumes"] = [costume(fn, label, 65, 23)]
    return sp, (fn, svg)


def build_boat(sid: str, boat_id: str, layer: int) -> tuple[dict, tuple[str, bytes]]:
    b = B()
    fn, svg = md5_asset(rect_svg(90, 40, "#ffffff", "Thuyen"), "svg")
    f = b.add("event_whenflagclicked", top=True, x=20, y=20, prefix="f")
    b.chain(f, b.add("looks_hide", prefix="h1"))
    sh = b.on_msg("batChoi", 20, 120)
    b.chain(sh, b.add("looks_show", prefix="sh"), b.add("motion_gotoxy", prefix="g", inputs={"X": b.num(0), "Y": b.num(140)}))
    add_hide_show(b, "ketThuc", True, 20, 220)

    fr = b.add("event_whenflagclicked", top=True, x=250, y=20, prefix="fr")
    lp = b.add("control_forever", prefix="lp")
    ifc = b.add("control_if", prefix="ifc")
    rk = b.add("sensing_keypressed", prefix="rk", fields={"KEY_OPTION": ["right arrow", None]})
    mv = b.add("motion_changexby", prefix="mv", inputs={"DX": b.num(9)})
    b.blocks[ifc]["inputs"] = {"CONDITION": [2, rk], "SUBSTACK": [2, mv]}
    b.blocks[mv]["parent"] = ifc
    ifl = b.add("control_if", prefix="ifl")
    lk = b.add("sensing_keypressed", prefix="lk", fields={"KEY_OPTION": ["left arrow", None]})
    mvl = b.add("motion_changexby", prefix="mvl", inputs={"DX": b.num(-9)})
    b.blocks[ifl]["inputs"] = {"CONDITION": [2, lk], "SUBSTACK": [2, mvl]}
    b.blocks[mvl]["parent"] = ifl
    b.blocks[lp]["inputs"] = {"SUBSTACK": [2, ifc]}
    b.blocks[ifc]["parent"] = lp
    b.chain(ifc, ifl)
    b.chain(fr, lp)

    sp = sprite_base("PhuongTien", sid, layer, 0, 140, 90)
    sp["blocks"] = b.blocks
    sp["costumes"] = [costume(fn, "Thuyen", 45, 20)]
    return sp, (fn, svg)


def build_claw(sid: str, boat_id: str, item_sids: dict[str, str], layer: int) -> tuple[dict, tuple[str, bytes]]:
    b = B()
    fn, svg = md5_asset(
        """<svg xmlns="http://www.w3.org/2000/svg" width="40" height="50">
<line x1="20" y1="0" x2="20" y2="18" stroke="#636e72" stroke-width="3"/>
<path d="M8 18 L20 30 L32 18 L28 42 L12 42 Z" fill="#0984e3" stroke="#2d3436"/>
</svg>""".encode(),
        "svg",
    )

    f = b.add("event_whenflagclicked", top=True, x=20, y=20, prefix="f")
    b.chain(
        f,
        b.add("looks_hide", prefix="h"),
        b.set_var("trangThai", "v_state", "lung"),
        b.set_var("daCam", "v_hold", 0),
        b.set_var("huongLung", "v_swing", 1),
    )

    sh = b.on_msg("batChoi", 20, 120)
    b.chain(
        sh,
        b.add("looks_show", prefix="sh"),
        b.set_var("trangThai", "v_state", "lung"),
        b.set_var("daCam", "v_hold", 0),
        b.add("motion_gotoxy", prefix="gp", inputs={"X": b.num(0), "Y": b.num(100)}),
        b.add("pen_clear", prefix="pc"),
        b.add("pen_setPenSizeTo", prefix="ps", inputs={"SIZE": b.num(2)}),
    )
    add_hide_show(b, "ketThuc", True, 20, 220)

    # pendulum + rope
    fr = b.add("event_whenflagclicked", top=True, x=260, y=20, prefix="fr")
    lp = b.add("control_forever", prefix="lp")
    iff = b.add("control_if", prefix="iff")
    st = b.eq_var("trangThai", "v_state", "lung", iff)
    bx = b.add("sensing_of", prefix="bx", fields={"PROPERTY": ["x position", None], "OBJECT": ["PhuongTien", boat_id]})
    sx = b.add("motion_setx", prefix="sx")
    b.blocks[sx]["inputs"] = {"X": [2, bx]}
    sy = b.add("motion_sety", prefix="sy", inputs={"Y": b.num(100)})
    mvsw = b.add("motion_changexby", prefix="mvsw")
    swv = b.var("huongLung", "v_swing", mvsw)
    b.blocks[mvsw]["inputs"] = {"DX": [2, swv]}
    dx = b.add("operator_subtract", prefix="dx")
    mx = b.add("motion_xposition", prefix="mx")
    b.blocks[dx]["inputs"] = {"NUM1": [2, mx], "NUM2": [2, bx]}
    ifsw = b.add("control_if", prefix="ifsw")
    gt2 = b.add("operator_gt", prefix="gt2")
    b.blocks[gt2]["inputs"] = {"OPERAND1": [2, dx], "OPERAND2": b.num(35)}
    flip = b.set_var("huongLung", "v_swing", -1)
    b.blocks[ifsw]["inputs"] = {"CONDITION": [2, gt2], "SUBSTACK": [2, flip]}
    ifsw2 = b.add("control_if", prefix="ifsw2")
    lt = b.add("operator_lt", prefix="lt")
    b.blocks[lt]["inputs"] = {"OPERAND1": [2, dx], "OPERAND2": b.num(-35)}
    flip2 = b.set_var("huongLung", "v_swing", 1)
    b.blocks[ifsw2]["inputs"] = {"CONDITION": [2, lt], "SUBSTACK": [2, flip2]}
    b.blocks[iff]["inputs"] = {"CONDITION": [2, st], "SUBSTACK": [2, sx]}
    b.chain(sx, sy, mvsw, ifsw, ifsw2)
    pen = b.add("pen_clear", prefix="pen")
    pu = b.add("pen_penUp", prefix="pu")
    gtboat = b.add("motion_gotoxy", prefix="gtb")
    bxb = b.add("sensing_of", prefix="bxb", fields={"PROPERTY": ["x position", None], "OBJECT": ["PhuongTien", boat_id]})
    b.blocks[gtboat]["inputs"] = {"X": [2, bxb], "Y": b.num(140)}
    pd = b.add("pen_penDown", prefix="pd")
    gtc = b.add("motion_gotoxy", prefix="gtc")
    mx2 = b.add("motion_xposition", prefix="mx2")
    my2 = b.add("motion_yposition", prefix="my2")
    b.blocks[gtc]["inputs"] = {"X": [2, mx2], "Y": [2, my2]}
    pup = b.add("pen_penUp", prefix="pup")
    b.chain(iff, pen, pu, gtboat, pd, gtc, pup)
    b.blocks[lp]["inputs"] = {"SUBSTACK": [2, iff]}
    b.blocks[iff]["parent"] = lp
    b.chain(fr, lp)

    # space - drop claw
    spk = b.add("event_whenkeypressed", top=True, x=260, y=260, prefix="spk")
    spk_fields = {"KEY_OPTION": ["space", None]}
    b.blocks[spk]["fields"] = spk_fields
    ifsp = b.add("control_if", prefix="ifsp")
    stl = b.eq_var("trangThai", "v_state", "lung", ifsp)
    b.blocks[ifsp]["inputs"] = {"CONDITION": [2, stl], "SUBSTACK": [2, None]}
    sx0 = b.set_var("trangThai", "v_state", "xuong")
    sx1 = b.set_var("daCam", "v_hold", 0)
    rp = b.add("control_repeat_until", prefix="rp")
    ed = b.add("operator_or", prefix="ed")
    yl = b.add("operator_lt", prefix="yl")
    yp = b.add("motion_yposition", prefix="yp")
    b.blocks[yl]["inputs"] = {"OPERAND1": [2, yp], "OPERAND2": b.num(-165)}
    hd = b.eq_var("daCam", "v_hold", 1, ed)
    b.blocks[ed]["inputs"] = {"OPERAND1": [2, yl], "OPERAND2": [2, hd]}
    b.blocks[rp]["inputs"] = {"CONDITION": [2, ed], "SUBSTACK": [2, None]}
    dn = b.add("motion_changeyby", prefix="dn", inputs={"DY": b.num(-7)})
    b.blocks[rp]["inputs"]["SUBSTACK"] = [2, dn]
    # catch checks for each item
    last = dn
    for iname, _, _, pts, *_ in ITEMS:
        ifc2 = b.add("control_if", prefix="ifc2")
        tc = b.add(
            "sensing_touchingobject",
            prefix="tc",
            fields={"TOUCHINGOBJECTMENU": [iname, item_sids[iname]]},
        )
        hd0 = b.eq_var("daCam", "v_hold", 0, ifc2)
        both = b.add("operator_and", prefix="ba")
        b.blocks[both]["inputs"] = {"OPERAND1": [2, tc], "OPERAND2": [2, hd0]}
        b.blocks[ifc2]["inputs"] = {"CONDITION": [2, both], "SUBSTACK": [2, None]}
        s1 = b.set_var("daCam", "v_hold", 1)
        s2 = b.change_var("diem", "g_score", pts)
        say = b.add(
            "looks_sayforsecs",
            parent=s2,
            inputs={"MESSAGE": b.txt(f"{'+' if pts > 0 else ''}{pts}"), "SECS": b.num(0.5)},
        )
        bbc = b.broadcast("daGap", say)
        b.blocks[ifc2]["inputs"]["SUBSTACK"] = [2, s1]
        b.chain(s1, s2, say, bbc)
        b.chain(last, ifc2)
        last = ifc2
    miss = b.add("control_if", prefix="miss")
    hd1 = b.eq_var("daCam", "v_hold", 0, miss)
    b.blocks[miss]["inputs"] = {"CONDITION": [2, hd1], "SUBSTACK": [2, b.broadcast("gapTruot")]}
    up = b.set_var("trangThai", "v_state", "len")
    rp2 = b.add("control_repeat_until", prefix="rp2")
    yg = b.add("operator_gt", prefix="yg")
    yp2 = b.add("motion_yposition", prefix="yp2")
    b.blocks[yg]["inputs"] = {"OPERAND1": [2, yp2], "OPERAND2": b.num(100)}
    b.blocks[rp2]["inputs"] = {"CONDITION": [2, yg], "SUBSTACK": [2, None]}
    upm = b.add("motion_changeyby", prefix="upm", inputs={"DY": b.num(7)})
    b.blocks[rp2]["inputs"]["SUBSTACK"] = [2, upm]
    fin = b.set_var("trangThai", "v_state", "lung")
    dec = b.change_var("luot", "g_turns", -1)
    rst = b.broadcast("datVat", dec)
    b.chain(spk, ifsp, sx0, sx1, rp, miss, up, rp2, fin, dec, rst)
    b.blocks[ifsp]["inputs"]["SUBSTACK"] = [2, sx0]
    b.chain(sx0, sx1, rp, miss, up, rp2, fin, dec, rst)

    sp = sprite_base("TayGap", sid, layer, 0, 100, 80)
    sp["variables"] = {
        "v_state": ["trangThai", "lung"],
        "v_hold": ["daCam", 0],
        "v_swing": ["huongLung", 1],
    }
    sp["blocks"] = b.blocks
    sp["costumes"] = [costume(fn, "TayGap", 20, 25)]
    return sp, (fn, svg)


def build_item(
    iname: str,
    label: str,
    color: str,
    points: int,
    x: int,
    y: int,
    moves: bool,
    sid: str,
    claw_id: str,
    layer: int,
) -> tuple[dict, tuple[str, bytes]]:
    b = B()
    fn, svg = md5_asset(rect_svg(44, 44, color, str(points)), "svg")
    f = b.add("event_whenflagclicked", top=True, x=20, y=20, prefix="f")
    b.chain(
        f,
        b.add("looks_hide", prefix="h"),
        b.set_var("biGap", "v_got", 0),
        b.add("motion_gotoxy", prefix="home", inputs={"X": b.num(x), "Y": b.num(y)}),
    )
    sh = b.on_msg("batChoi", 20, 120)
    b.chain(
        sh,
        b.add("looks_show", prefix="sh"),
        b.set_var("biGap", "v_got", 0),
        b.add("motion_gotoxy", prefix="g", inputs={"X": b.num(x), "Y": b.num(y)}),
    )
    rs = b.on_msg("datVat", 20, 220)
    b.chain(
        rs,
        b.set_var("biGap", "v_got", 0),
        b.add("looks_show", prefix="sh2"),
        b.add("motion_gotoxy", prefix="g2", inputs={"X": b.num(x), "Y": b.num(y)}),
    )
    add_hide_show(b, "ketThuc", True, 20, 320)

    if moves:
        fr = b.add("event_whenflagclicked", top=True, x=260, y=20, prefix="fr")
        lp = b.add("control_forever", prefix="lp")
        iff = b.add("control_if", prefix="iff")
        bg = b.eq_var("biGap", "v_got", 0, iff)
        mv = b.add("motion_changexby", prefix="mv", inputs={"DX": b.num(3)})
        bn = b.add("motion_ifonedgebounce", prefix="bn")
        b.blocks[iff]["inputs"] = {"CONDITION": [2, bg], "SUBSTACK": [2, mv]}
        b.blocks[mv]["parent"] = iff
        b.chain(mv, bn)
        b.blocks[lp]["inputs"] = {"SUBSTACK": [2, iff]}
        b.blocks[iff]["parent"] = lp
        b.chain(fr, lp)

    fr2 = b.add("event_whenflagclicked", top=True, x=260, y=160, prefix="fr2")
    lp2 = b.add("control_forever", prefix="lp2")
    ifg = b.add("control_if", prefix="ifg")
    g1 = b.eq_var("biGap", "v_got", 1, ifg)
    b.blocks[ifg]["inputs"] = {"CONDITION": [2, g1], "SUBSTACK": [2, None]}
    gt = b.add("motion_gotoxy", prefix="gt")
    cx = b.add("sensing_of", prefix="cx", fields={"PROPERTY": ["x position", None], "OBJECT": ["TayGap", claw_id]})
    cy = b.add("sensing_of", prefix="cy", fields={"PROPERTY": ["y position", None], "OBJECT": ["TayGap", claw_id]})
    b.blocks[gt]["inputs"] = {"X": [2, cx], "Y": [2, cy]}
    b.blocks[ifg]["inputs"]["SUBSTACK"] = [2, gt]
    b.blocks[gt]["parent"] = ifg
    b.blocks[lp2]["inputs"] = {"SUBSTACK": [2, ifg]}
    b.blocks[ifg]["parent"] = lp2
    b.chain(fr2, lp2)

    og = b.on_msg("daGap", 260, 260)
    ifd = b.add("control_if", prefix="ifd")
    tc = b.add(
        "sensing_touchingobject",
        prefix="tc",
        fields={"TOUCHINGOBJECTMENU": ["TayGap", claw_id]},
    )
    b.blocks[ifd]["inputs"] = {"CONDITION": [2, tc], "SUBSTACK": [2, b.set_var("biGap", "v_got", 1)]}
    b.chain(og, ifd)

    sp = sprite_base(iname, sid, layer, x, y, 80 if points > 0 else 70)
    sp["variables"] = {"v_got": ["biGap", 0]}
    sp["blocks"] = b.blocks
    sp["costumes"] = [costume(fn, label, 22, 22)]
    return sp, (fn, svg)


def build_stage(assets: list[tuple[str, bytes]]) -> dict:
    bds = [
        ("Mo dau", backdrop_svg(
            "JUST DROP IT",
            "Phim trai/phai: di chuyen thuyen | Space: tha tay gap",
            "#2d3436",
            '<text x="240" y="140" font-family="Arial" font-size="12" fill="#dfe6e9" text-anchor="middle">Gap vat tot (+) va tranh bom/ran (-)</text>',
        )),
        ("Choi", underwater_bg()),
        ("Ket thuc", backdrop_svg("HET LUOT!", "Xem diem va bam Choi lai", "#6c5ce7")),
    ]
    backdrop_ids: dict[str, str] = {}
    costumes = []
    for disp, svg in bds:
        fn, data = md5_asset(svg if isinstance(svg, bytes) else svg, "svg")
        backdrop_ids[disp] = fn.split(".")[0]
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

    b = B()
    f = b.add("event_whenflagclicked", top=True, x=20, y=20, prefix="f")
    b.chain(f, b.broadcast("datLai"))

    r = b.on_msg("datLai", 20, 120)
    sw = b.add("looks_switchbackdropto", prefix="sw")
    b.blocks[sw]["fields"] = {"BACKDROP": ["Mo dau", backdrop_ids["Mo dau"]]}
    b.chain(
        r,
        sw,
        b.set_var("diem", "g_score", 0),
        b.set_var("luot", "g_turns", 10),
        b.set_var("level", "g_level", 1),
    )

    s = b.on_msg("batDau", 200, 120)
    sw1 = b.add("looks_switchbackdropto", prefix="sw1")
    b.blocks[sw1]["fields"] = {"BACKDROP": ["Choi", backdrop_ids["Choi"]]}
    b.chain(
        s,
        sw1,
        b.set_var("diem", "g_score", 0),
        b.set_var("luot", "g_turns", 10),
        b.set_var("level", "g_level", 1),
        b.broadcast("batChoi"),
    )

    c = b.on_msg("batChoi", 360, 120)
    swc = b.add("looks_switchbackdropto", prefix="swc")
    b.blocks[swc]["fields"] = {"BACKDROP": ["Choi", backdrop_ids["Choi"]]}
    b.chain(c, swc, b.broadcast("batChoi"))

    fr = b.on_msg("batChoi", 360, 220)
    lp = b.add("control_forever", prefix="lp")
    if0 = b.add("control_if", prefix="if0")
    z = b.eq_var("luot", "g_turns", 0, if0)
    w = b.add("control_wait", prefix="w", inputs={"DURATION": b.num(0.1)})
    end = b.broadcast("ketThuc", w)
    b.blocks[if0]["inputs"] = {"CONDITION": [2, z], "SUBSTACK": [2, w]}
    b.blocks[lp]["inputs"] = {"SUBSTACK": [2, if0]}
    b.blocks[if0]["parent"] = lp
    b.chain(fr, lp)

    e = b.on_msg("ketThuc", 20, 320)
    sw3 = b.add("looks_switchbackdropto", prefix="sw3")
    b.blocks[sw3]["fields"] = {"BACKDROP": ["Ket thuc", backdrop_ids["Ket thuc"]]}
    msg = b.add("looks_sayforsecs", prefix="msg", inputs={"MESSAGE": b.txt("Ket thuc!"), "SECS": b.num(2)})
    b.chain(e, sw3, msg)

    ok = b.on_msg("daGap", 520, 120)
    b.chain(ok, b.play_pop())
    miss = b.on_msg("gapTruot", 520, 220)
    b.chain(miss, b.play_pop())

    return {
        "isStage": True,
        "name": "Stage",
        "id": scratch_id(),
        "variables": {
            "g_score": ["diem", 0],
            "g_turns": ["luot", 10],
            "g_level": ["level", 1],
        },
        "lists": {
            "list_items": ["danhSachVat", [f"{n}({p:+d})" for n, _, _, p, *_ in ITEMS]],
        },
        "broadcasts": {BROADCAST_IDS[k]: BROADCAST_LABELS[k] for k in BROADCAST_LABELS},
        "blocks": b.blocks,
        "comments": {},
        "currentCostume": 0,
        "costumes": costumes,
        "sounds": [
            {
                "assetId": "83a9787d4cb6f3b7632b4ddfebf74367",
                "name": "pop",
                "dataFormat": "wav",
                "format": "",
                "rate": 48000,
                "sampleCount": 1123,
                "md5ext": "83a9787d4cb6f3b7632b4ddfebf74367.wav",
            }
        ],
        "volume": 100,
        "layerOrder": 0,
        "tempo": 60,
        "videoTransparency": 50,
        "videoState": "off",
        "textToSpeechLanguage": None,
    }


def build_project() -> tuple[dict, list[tuple[str, bytes]]]:
    assets: list[tuple[str, bytes]] = []
    ids = {n: scratch_id() for n in [
        "PhuongTien", "TayGap", "BtnBatDau", "BtnChoiLai", *[i[0] for i in ITEMS],
    ]}
    stage = build_stage(assets)
    targets = [stage]
    layer = 1

    btn1, a1 = build_button("BtnBatDau", "Bat dau", "batDau", 0, -130, layer, ids["BtnBatDau"])
    assets.append(a1)
    targets.append(btn1)
    layer += 1

    btn2, a2 = build_button("BtnChoiLai", "Choi lai", "batChoi", 0, -130, layer, ids["BtnChoiLai"])
    assets.append(a2)
    targets.append(btn2)
    layer += 1

    boat, ab = build_boat(ids["PhuongTien"], ids["PhuongTien"], layer)
    assets.append(ab)
    targets.append(boat)
    layer += 1

    claw, ac = build_claw(ids["TayGap"], ids["PhuongTien"], ids, layer)
    assets.append(ac)
    targets.append(claw)
    layer += 1

    for iname, label, color, pts, x, y, moves in ITEMS:
        sp, asset = build_item(iname, label, color, pts, x, y, moves, ids[iname], ids["TayGap"], layer)
        assets.append(asset)
        targets.append(sp)
        layer += 1

    for t in targets:
        patch = B()
        nm = t.get("name", "")
        if nm == "BtnChoiLai":
            add_hide_show(patch, "batChoi", True, 0, 0)
            add_hide_show(patch, "datLai", True, 100, 0)
            h = patch.on_msg("ketThuc", 200, 0)
            patch.chain(h, patch.add("looks_show", prefix="sh"))
        if patch.blocks:
            t["blocks"].update(patch.blocks)

    project = {
        "targets": targets,
        "monitors": [
            {
                "id": "g_score",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "diem"},
                "spriteName": None,
                "value": 0,
                "width": 0,
                "height": 0,
                "x": 5,
                "y": 5,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 200,
                "isDiscrete": True,
            },
            {
                "id": "g_turns",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "luot"},
                "spriteName": None,
                "value": 10,
                "width": 0,
                "height": 0,
                "x": 5,
                "y": 35,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 20,
                "isDiscrete": True,
            },
        ],
        "extensions": ["pen"],
        "meta": {
            "semver": "3.0.0",
            "vm": "0.2.0-prerelease.20220510130158",
            "agent": "just-drop-it-v1",
        },
    }
    return project, assets


def write_sb3(project: dict, assets: list[tuple[str, bytes]], output: Path) -> None:
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "project.json",
            json.dumps(project, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        )
        for n, d in assets:
            z.writestr(n, d)
        if POP_WAV.exists():
            with zipfile.ZipFile(POP_WAV) as tmpl:
                z.writestr("83a9787d4cb6f3b7632b4ddfebf74367.wav", tmpl.read("83a9787d4cb6f3b7632b4ddfebf74367.wav"))


def main() -> None:
    if not POP_WAV.exists():
        import urllib.request
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/scratchfoundation/scratch-vm/develop/test/fixtures/default.sb3",
            POP_WAV,
        )
    project, assets = build_project()
    write_sb3(project, assets, OUTPUT)
    print(f"OK: {OUTPUT}  sprites={len(project['targets'])}  assets={len(assets)+1}")


if __name__ == "__main__":
    main()
