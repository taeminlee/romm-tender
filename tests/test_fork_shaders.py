"""Fork addition: fork_shaders installs the server's shader bundle into RetroArch's shader folder."""

import io
import os
import tarfile
import urllib.error

import fork_shaders
import pytest

RA = (".var", "app", "net.retrodeck.retrodeck", "config", "retroarch")


def _bundle(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


GOOD = {
    "guest/schM0ggi_SNES.slangp": b"g",
    "hb-upscale/A + CRT.slangp": b"a",
    "hb-upscale/shaders/x.slang": b"x",
    "real-crt-phosphor/p.slangp": b"p",
}


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _home(tmp_path, shader_dir_line=None):
    cfg_dir = tmp_path.joinpath(*RA)
    cfg_dir.mkdir(parents=True)
    lines = 'video_driver = "vulkan"\n' + (shader_dir_line or "")
    (cfg_dir / "retroarch.cfg").write_text(lines)
    return str(tmp_path), str(cfg_dir / "shaders")


def _serve(monkeypatch, data=None, error=None):
    def fake(url, insecure, headers):
        assert url == "https://romm.example/hb/deck/deck-shaders.tar.gz"
        if error:
            raise error
        return data

    monkeypatch.setattr(fork_shaders, "_download", fake)


def test_installs_and_replaces_bundle_folders(tmp_path, monkeypatch):
    home, sh = _home(tmp_path)
    stale = os.path.join(sh, "shaders_slang", "hb-upscale", "old.slangp")
    os.makedirs(os.path.dirname(stale))
    open(stale, "w").close()
    keep = os.path.join(sh, "shaders_slang", "crt", "keep.slangp")
    os.makedirs(os.path.dirname(keep))
    open(keep, "w").close()
    _serve(monkeypatch, _bundle(GOOD))

    r = fork_shaders.install("https://romm.example/", False, {}, home)

    assert r == {"success": True, "shader_dir": sh, "presets": ["A + CRT.slangp"]}
    assert not os.path.exists(stale)
    assert os.path.exists(keep)
    assert _read(os.path.join(sh, "shaders_slang", "hb-upscale", "shaders", "x.slang")) == b"x"
    assert _read(os.path.join(sh, "schM0ggi_SNES.slangp")) == b"g"
    assert [n for n in os.listdir(os.path.join(sh, "shaders_slang")) if n.startswith(".tender")] == []


@pytest.mark.parametrize("bad", ["../evil.slangp", "/abs.slangp", "other/x.slang", "hb-upscale/../../x"])
def test_rejects_entries_outside_the_bundle(tmp_path, monkeypatch, bad):
    home, sh = _home(tmp_path)
    _serve(monkeypatch, _bundle({**GOOD, bad: b"!"}))

    r = fork_shaders.install("https://romm.example", False, {}, home)

    assert r["success"] is False and r["reason"] == "bad_bundle" and r["message"]
    assert not os.path.exists(os.path.join(sh, "shaders_slang", "hb-upscale"))


def test_rejects_links(tmp_path, monkeypatch):
    home, _ = _home(tmp_path)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("hb-upscale/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tar.addfile(info)
    _serve(monkeypatch, buf.getvalue())

    assert fork_shaders.install("https://romm.example", False, {}, home)["reason"] == "bad_bundle"


def test_server_without_bundle(tmp_path, monkeypatch):
    home, _ = _home(tmp_path)
    _serve(monkeypatch, error=urllib.error.HTTPError("u", 404, "nf", None, None))

    r = fork_shaders.install("https://romm.example", False, {}, home)

    assert r["success"] is False and r["reason"] == "not_offered"


def test_no_server_url(tmp_path):
    assert fork_shaders.install("", False, {}, str(tmp_path))["reason"] == "config_error"


def test_no_retroarch(tmp_path):
    assert fork_shaders.install("https://romm.example", False, {}, str(tmp_path))["reason"] == "not_installed"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ('video_shader_dir = "default"\n', ("cfg", "shaders")),
        ('video_shader_dir = "~/retrodeck/shaders"\n', ("home", "retrodeck/shaders")),
        ('video_shader_dir = ":/myshaders"\n', ("cfg", "myshaders")),
        ('video_shader_dir = "/run/media/sd/shaders"\n', ("abs", "/run/media/sd/shaders")),
    ],
)
def test_shader_dir_follows_retroarch_cfg(tmp_path, line, expected):
    home, _ = _home(tmp_path, line)
    cfg_dir = os.path.join(home, *RA)
    base = {"cfg": cfg_dir, "home": home, "abs": ""}[expected[0]]
    want = expected[1] if expected[0] == "abs" else os.path.join(base, expected[1])
    assert fork_shaders.shader_dir(home) == want
