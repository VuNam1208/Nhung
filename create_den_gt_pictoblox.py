#!/usr/bin/env python3
"""Generate PictoBlox Upload Mode project: vehicle traffic light on pins 2,3,4."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

TEMPLATE = Path(
    "/tmp/uno/sunfounder-uno-and-mega-kit-master/scratch(uno)/code/1. Upload Mode.sb3"
)
OUTPUT = Path(__file__).with_name("den-giao-thong-xe-pictoblox.sb3")

# Pin mapping: R=2, Y=3, G=4
PINS = {"do": "2", "vang": "3", "xanh": "4"}


class B:
    def __init__(self) -> None:
        self.blocks: dict[str, dict] = {}
        self.n = 0

    def nid(self, prefix: str = "b") -> str:
        self.n += 1
        return f"{prefix}{self.n}"

    def add(
        self,
        opcode: str,
        *,
        parent: str | None = None,
        inputs: dict | None = None,
        fields: dict | None = None,
        top: bool = False,
        x: int = 0,
        y: int = 0,
        prefix: str = "b",
    ) -> str:
        bid = self.nid(prefix)
        block: dict = {
            "opcode": opcode,
            "next": None,
            "parent": parent,
            "inputs": inputs or {},
            "fields": fields or {},
            "shadow": False,
            "topLevel": top,
        }
        if top:
            block["x"] = x
            block["y"] = y
        self.blocks[bid] = block
        return bid

    def chain(self, *ids: str) -> None:
        for a, c in zip(ids, ids[1:]):
            self.blocks[a]["next"] = c
            self.blocks[c]["parent"] = a

    def wait(self, seconds: str, parent: str | None = None) -> str:
        return self.add(
            "control_wait",
            parent=parent,
            inputs={"DURATION": [1, [5, seconds]]},
            prefix="w",
        )

    def pin(self, pin: str, high: bool, parent: str | None = None) -> str:
        return self.add(
            "arduinoUno_digitalWrite",
            parent=parent,
            fields={"PIN": [pin, None], "MODE": ["true" if high else "false", None]},
            prefix="p",
        )


def set_all_lights(b: B, red: bool, yellow: bool, green: bool) -> list[str]:
  ids = [
      b.pin(PINS["do"], red),
      b.pin(PINS["vang"], yellow),
      b.pin(PINS["xanh"], green),
  ]
  b.chain(*ids)
  return ids


def build_blocks() -> dict[str, dict]:
    b = B()

    startup = b.add("arduinoUno_arduinoUnoStartUp", top=True, x=120, y=40, prefix="hat")
    forever = b.add("control_forever", parent=startup, prefix="f")
    b.chain(startup, forever)

    g1, g2, g3 = set_all_lights(b, False, False, True)
    w1 = b.wait("5", g3)
    b.chain(g3, w1)

    y1, y2, y3 = set_all_lights(b, False, True, False)
    b.chain(w1, y1)
    w2 = b.wait("2", y3)
    b.chain(y3, w2)

    r1, r2, r3 = set_all_lights(b, True, False, False)
    b.chain(w2, r1)
    w3 = b.wait("5", r3)
    b.chain(r3, w3)

    b.blocks[forever]["inputs"] = {"SUBSTACK": [2, g1]}
    b.blocks[g1]["parent"] = forever

    return b.blocks


def main() -> None:
    if not TEMPLATE.exists():
        raise SystemExit(f"Missing template: {TEMPLATE}")

    with zipfile.ZipFile(TEMPLATE, "r") as zin:
        project = json.loads(zin.read("project.json"))

    for target in project["targets"]:
        if not target.get("isStage"):
            target["name"] = "Den GT Xe"
            target["blocks"] = build_blocks()

    project["meta"]["agent"] = "den-giao-thong-xe-generator"

    new_json = json.dumps(project, ensure_ascii=False).encode("utf-8")

    with zipfile.ZipFile(TEMPLATE, "r") as zin, zipfile.ZipFile(OUTPUT, "w") as zout:
        for item in zin.infolist():
            data = new_json if item.filename == "project.json" else zin.read(item.filename)
            zout.writestr(item, data)

    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()
