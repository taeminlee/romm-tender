"""Fork addition (0.33.1-msu6): install the RetroArch shader bundle the RomM server offers.

The RomM this fork targets runs an add-on that serves a slang shader bundle at
``<server>/hb/deck/deck-shaders.tar.gz`` (CuNNy / MMPX+CuNNy upscalers with CRT
and LCD combos matching the server's web player, Real CRT Phosphor, Guest
Advanced presets). Until now it was installed with a ``curl | bash`` script; this
does the same from the QAM so no terminal is needed.

What it changes, all under RetroArch's ``video_shader_dir`` (read from the same
``retroarch.cfg`` candidates the rest of the plugin uses):

- ``shaders_slang/hb-upscale`` and ``shaders_slang/real-crt-phosphor`` are
  replaced wholesale by the bundle's copies (they hold nothing but the bundle);
- the bundle's ``guest/*.slangp`` presets are copied to the shader root.

The archive is untrusted input: only regular files and directories under the
three known top-level folders are accepted, with no absolute paths, no ``..``
and no links, and its size is capped.
"""

from __future__ import annotations

import io
import os
import shutil
import ssl
import tarfile
import tempfile
import urllib.error
import urllib.request
from typing import Any

from lib.certifi_bundle import ca_bundle

BUNDLE_PATH = "/hb/deck/deck-shaders.tar.gz"
MAX_BYTES = 64 * 1024 * 1024
TOP_DIRS = ("guest", "hb-upscale", "real-crt-phosphor")
REPLACED = ("hb-upscale", "real-crt-phosphor")
_RA_CFGS = (
    (".var", "app", "net.retrodeck.retrodeck", "config", "retroarch", "retroarch.cfg"),
    (".var", "app", "org.libretro.RetroArch", "config", "retroarch", "retroarch.cfg"),
    (".config", "retroarch", "retroarch.cfg"),
)


def _fail(reason: str, message: str) -> dict[str, Any]:
    return {"success": False, "reason": reason, "message": message}


def shader_dir(user_home: str) -> str | None:
    """RetroArch's shader directory, or None when no RetroArch config exists yet."""
    for parts in _RA_CFGS:
        cfg = os.path.join(user_home, *parts)
        if not os.path.isfile(cfg):
            continue
        value = ""
        with open(cfg, encoding="utf-8", errors="replace") as f:
            for line in f:
                key, _, raw = line.partition("=")
                if key.strip() == "video_shader_dir":
                    value = raw.strip().strip('"')
                    break
        base = os.path.dirname(cfg)
        if value in ("", "default"):
            return os.path.join(base, "shaders")
        if value.startswith("~/"):
            return os.path.join(user_home, value[2:])
        if value.startswith(":/"):
            return os.path.join(base, value[2:])
        return value
    fallback = os.path.join(user_home, "retrodeck", "shaders")
    return fallback if os.path.isdir(fallback) else None


def _download(url: str, insecure: bool, headers: dict[str, str]) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Tender", **headers})
    # Decky's Python has no system CA store; use the certifi bundle like the RomM client (msu9 fix).
    ctx = ssl.create_default_context(cafile=ca_bundle())
    if insecure:  # the user's own "allow insecure SSL" server setting
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("bundle too large")
    return data


def _safe_members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = []
    for m in tar.getmembers():
        name = m.name
        parts = name.split("/")
        if name.startswith("/") or ".." in parts or parts[0] not in TOP_DIRS or not (m.isfile() or m.isdir()):
            raise ValueError(f"unexpected entry {name!r}")
        members.append(m)
    return members


def install(romm_url: str, insecure: bool, headers: dict[str, str], user_home: str) -> dict[str, Any]:
    """Download the server's shader bundle and install it into RetroArch's shader folder.

    Returns ``{success: True, shader_dir, presets}`` (``presets``: the combo
    presets now in ``shaders_slang/hb-upscale``) or the
    ``{success: False, reason, message}`` failure shape.
    """
    if not romm_url:
        return _fail("config_error", "RomM 서버 주소가 설정되지 않았습니다.")
    target = shader_dir(user_home)
    if not target:
        return _fail(
            "not_installed",
            "RetroArch 설정을 찾지 못했습니다. RetroDECK 에서 RetroArch 를 한 번 실행한 뒤 다시 해 주세요.",
        )
    url = romm_url.rstrip("/") + BUNDLE_PATH
    try:
        data = _download(url, insecure, headers)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return _fail("not_offered", "이 서버는 셰이더 묶음을 제공하지 않습니다.")
        return _fail("server_unreachable", f"셰이더 묶음을 받지 못했습니다 (HTTP {e.code}).")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return _fail("server_unreachable", f"셰이더 묶음을 받지 못했습니다: {e}")

    slang = os.path.join(target, "shaders_slang")
    try:
        os.makedirs(slang, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=slang, prefix=".tender-shaders-") as tmp:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                members = _safe_members(tar)
                for m in members:
                    dest = os.path.join(tmp, *m.name.split("/"))
                    if m.isdir():
                        os.makedirs(dest, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    src = tar.extractfile(m)
                    if src is None:
                        raise ValueError(f"unreadable entry {m.name!r}")
                    with src, open(dest, "wb") as out:
                        shutil.copyfileobj(src, out)
            if not all(os.path.isdir(os.path.join(tmp, d)) for d in TOP_DIRS):
                raise ValueError("bundle is missing a folder")
            for d in REPLACED:
                shutil.rmtree(os.path.join(slang, d), ignore_errors=True)
                os.replace(os.path.join(tmp, d), os.path.join(slang, d))
            guest = os.path.join(tmp, "guest")
            for fn in sorted(os.listdir(guest)):
                if fn.endswith(".slangp"):
                    shutil.copyfile(os.path.join(guest, fn), os.path.join(target, fn))
    except (tarfile.TarError, ValueError) as e:
        return _fail("bad_bundle", f"셰이더 묶음이 올바르지 않습니다: {e}")
    except OSError as e:
        return _fail("io_error", f"셰이더를 설치하지 못했습니다: {e}")

    hb = os.path.join(slang, "hb-upscale")
    presets = sorted(fn for fn in os.listdir(hb) if fn.endswith(".slangp"))
    return {"success": True, "shader_dir": target, "presets": presets}
