#!/usr/bin/env bash
# =============================================================================
#  setup.sh - Clone xiaozhi-esp32 and register the DIYMORE ESP32-S3 2.8" board
#
#  Run this on YOUR OWN computer (Linux/macOS/WSL) where ESP-IDF is installed
#  and where the board is plugged in over USB-C. This script only prepares the
#  source tree; flashing is a separate step (see the printed instructions).
#
#  Usage:
#     ./setup.sh                # clones into ./xiaozhi-esp32 next to this repo
#     ./setup.sh /path/to/dest  # clones into a directory you choose
# =============================================================================
set -euo pipefail

BOARD="diymore-esp32s3-2p8-touch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-$SCRIPT_DIR/xiaozhi-esp32}"
REPO="https://github.com/78/xiaozhi-esp32.git"

echo ">> Target board : $BOARD"
echo ">> Destination  : $DEST"

# 1) Clone (or reuse) the xiaozhi-esp32 source tree
if [ ! -d "$DEST/.git" ]; then
    echo ">> Cloning $REPO ..."
    git clone --depth 1 "$REPO" "$DEST"
else
    echo ">> Repo already present, skipping clone."
fi

# 2) Copy the custom board folder into main/boards/
echo ">> Copying board files into main/boards/$BOARD ..."
mkdir -p "$DEST/main/boards/$BOARD"
cp -f "$SCRIPT_DIR/boards/$BOARD/"* "$DEST/main/boards/$BOARD/"

# 3) Register the board in Kconfig.projbuild and CMakeLists.txt (idempotent)
echo ">> Registering board in the build system ..."
python3 - "$DEST" "$BOARD" <<'PY'
import sys, pathlib

dest, board = sys.argv[1], sys.argv[2]
kconfig = pathlib.Path(dest, "main", "Kconfig.projbuild")
cmake   = pathlib.Path(dest, "main", "CMakeLists.txt")

# Derive a Kconfig symbol, e.g. diymore-esp32s3-2p8-touch -> DIYMORE_ESP32S3_2P8_TOUCH
sym = "BOARD_TYPE_" + board.upper().replace("-", "_").replace(".", "_")

# ---- Kconfig.projbuild ----
k = kconfig.read_text()
if sym not in k:
    anchor = "config BOARD_TYPE_Freenove_ESP32S3_DISPLAY_2_8_LCD"
    lines = k.splitlines(keepends=True)
    out, inserted = [], False
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if anchor in lines[i]:
            # skip the two following lines of the freenove block (bool + depends)
            for j in range(i + 1, min(i + 3, len(lines))):
                out.append(lines[j])
            block = (
                f"    config {sym}\n"
                f'        bool "DIYMORE ESP32-S3 2.8-inch Capacitive Touch LCD"\n'
                f"        depends on IDF_TARGET_ESP32S3\n"
            )
            out.append(block)
            inserted = True
            i += 3
            continue
        i += 1
    if not inserted:
        raise SystemExit("!! Could not find Freenove anchor in Kconfig.projbuild")
    kconfig.write_text("".join(out))
    print("   + Kconfig entry added.")
else:
    print("   = Kconfig entry already present.")

# ---- CMakeLists.txt ----
c = cmake.read_text()
if f"CONFIG_{sym}" not in c:
    anchor = "elseif(CONFIG_BOARD_TYPE_Freenove_ESP32S3_DISPLAY_2_8_LCD)"
    idx = c.find(anchor)
    if idx == -1:
        raise SystemExit("!! Could not find Freenove branch in CMakeLists.txt")
    # find the start of the NEXT branch after the freenove block
    nxt = c.find("elseif(", idx + len(anchor))
    branch = (
        f"elseif(CONFIG_{sym})\n"
        f'    set(BOARD_DIR "{board}")\n'
        f"    set(BUILTIN_TEXT_FONT font_noto_sans_basic_20_4)\n"
        f"    set(BUILTIN_ICON_FONT font_material_symbols_20_4)\n"
        f"    set(DEFAULT_EMOJI_COLLECTION noto-color-emoji_64)\n"
    )
    c = c[:nxt] + branch + c[nxt:]
    cmake.write_text(c)
    print("   + CMakeLists branch added.")
else:
    print("   = CMakeLists branch already present.")
PY

cat <<EOF

============================================================================
 Board registered. Next steps (run on your machine):

   cd "$DEST"
   . \$IDF_PATH/export.sh            # load ESP-IDF (v5.4+ recommended)
   idf.py set-target esp32s3
   idf.py menuconfig                # Xiaozhi Assistant -> Board Type
                                    #   -> "DIYMORE ESP32-S3 2.8-inch ..."
   idf.py build
   idf.py -p /dev/ttyACM0 flash monitor   # replace with your serial port

 TIP: This hardware matches the Freenove/LCDwiki ES3C28P design. If you want
      to skip the custom board, you can instead select the built-in target
      "Freenove ESP32-S3 Display 2.8-inch LCD" in menuconfig.
============================================================================
EOF
