# AGENTS.md

## Cursor Cloud specific instructions

This repo is an educational embedded/IoT bundle (Vietnamese), not a conventional web/app project. There is **no** `package.json`, `Makefile`, lockfile, or CI. The only locally runnable code is:

- **Python `.sb3` generators** (`create_*.py`) — build PictoBlox/Scratch project files. They use only the Python 3 standard library, so there is nothing to `pip install`. Run e.g. `python3 create_attendance_sb3.py`.
- **`esp.html`** — a static Firebase-backed web dashboard for the automatic street-lighting IoT product. Serve it with `python3 -m http.server 8000` from the repo root and open `http://localhost:8000/esp.html`. It connects to a live Firebase Realtime DB (project `iott-eddfb`) via anonymous auth and needs outbound network. The lamp-control buttons update the UI immediately and write commands to Firebase (no physical ESP32/STM32 hardware is required to exercise the dashboard).
- **`.ino` firmware** (`mainesp/mainesp.ino`, `stm32/stm32.ino`) — Arduino/ESP32/STM32 sketches. These require physical hardware + the Arduino toolchain (not installed) and cannot be run/flashed in this VM.

### SunFounder template dependency (non-obvious)

Three of the four generators (`create_cong_truong_pictoblox.py`, `create_den_gt_pictoblox.py`, `create_smart_crossing_pictoblox.py`) read a SunFounder UNO kit template from the hardcoded path `/tmp/uno/sunfounder-uno-and-mega-kit-master/scratch(uno)/code/`. `/tmp` is ephemeral, so the startup update script re-downloads and extracts that template on each session. `create_attendance_sb3.py` is standalone and needs no template.

### Testing / verification

There are no automated tests. Verify generators by running them and confirming each output `.sb3` is a valid zip containing `project.json`. Verify the dashboard by loading `esp.html` in a browser and confirming the status pill shows "Đã login. Đang nghe realtime…" and the lamp control toggles the bulb. Regenerating `.sb3` files may show them as modified in git (some generators use random IDs); do not commit regenerated artifacts unless intentionally changing them.
