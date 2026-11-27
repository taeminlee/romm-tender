"""Fork addition (0.33.1-msu8): per-system frame generation switches.

``bin/rom-launcher`` starts a game through decky-lsfg-vk's ``~/lsfg`` script
when the ROM's RetroDECK system folder is chosen in
``~/.config/romm-tender/lsfg-systems`` (``*`` = every system, ``-name`` = never
that one, no file = every system). Editing that file by hand meant a terminal;
this reads and writes it for the switches under Settings › Advanced.

The answer lists the systems that have something in RetroDECK's ROM folder, so
the switches match what is installed. Writing keeps the file's names and only
adds or drops the one that changed (comments are replaced by a fixed header).
"""

from __future__ import annotations

import os
import re
from typing import Any

CONF_REL = (".config", "romm-tender", "lsfg-systems")
SCRIPT_REL = "lsfg"
DEFAULT = "*"
HEADER = (
    "# Frame generation (decky-lsfg-vk) per RetroDECK system, read by Tender's rom-launcher.\n"
    "# `*` = every system, a name = that system, `-name` = never that system.\n"
    "# Edited by Tender › Settings › Advanced (names are kept, comments are not).\n"
)
_NAME = re.compile(r"^[a-z0-9][a-z0-9_+-]{0,63}$")


def conf_path(home: str) -> str:
    return os.path.join(home, *CONF_REL)


def _tokens(home: str) -> list[str] | None:
    """The file's words without comments, or ``None`` when there is no file."""
    try:
        with open(conf_path(home), encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None
    words: list[str] = []
    for line in text.splitlines():
        words.extend(line.split("#", 1)[0].split())
    return words


def enabled_for(tokens: list[str] | None, system: str) -> bool:
    """Exactly the launcher's rule: an exclusion wins, then `*` or the name itself."""
    words = [DEFAULT] if tokens is None else tokens
    if f"-{system}" in words:
        return False
    return DEFAULT in words or system in words


def _installed_systems(roms_path: str) -> list[str]:
    try:
        entries = sorted(os.scandir(roms_path), key=lambda e: e.name)
    except OSError:
        return []
    found = []
    for e in entries:
        if not e.is_dir() or not _NAME.match(e.name):
            continue
        try:
            with os.scandir(e.path) as it:
                if any(not c.name.startswith(".") and c.name != "systeminfo.txt" for c in it):
                    found.append(e.name)
        except OSError:
            continue
    return found


def status(home: str, roms_path: str) -> dict[str, Any]:
    tokens = _tokens(home)
    script = os.path.join(home, SCRIPT_REL)
    return {
        "available": os.access(script, os.X_OK) and not os.path.isdir(script),
        "all": tokens is None or (DEFAULT in tokens),
        "systems": [{"name": s, "enabled": enabled_for(tokens, s)} for s in _installed_systems(roms_path)],
    }


def set_system(home: str, system: str, enabled: bool) -> dict[str, Any]:
    if not isinstance(system, str) or not _NAME.match(system):
        return {"success": False, "reason": "bad_system", "message": f"알 수 없는 시스템 이름: {system!r}"}
    tokens = _tokens(home)
    words = [DEFAULT] if tokens is None else list(tokens)
    words = [w for w in words if w not in (system, f"-{system}")]
    if enabled:
        if DEFAULT not in words:
            words.append(system)
    else:
        if DEFAULT in words:
            words.append(f"-{system}")
    path = conf_path(home)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(HEADER + " ".join(words) + "\n")
    os.replace(tmp, path)
    return {"success": True, "enabled": enabled_for(words, system)}
