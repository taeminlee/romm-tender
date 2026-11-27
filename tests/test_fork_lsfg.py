"""Fork addition (0.33.1-msu8): per-system frame generation switches and the launcher rule they feed."""

import os
import pathlib
import subprocess

import fork_lsfg
import pytest

LAUNCHER = pathlib.Path(__file__).resolve().parent.parent / "bin" / "rom-launcher"


def _home(tmp_path, conf=None, script=True):
    home = tmp_path / "home"
    home.mkdir()
    if script:
        s = home / "lsfg"
        s.write_text('#!/bin/sh\necho LSFG "$@"\n')
        s.chmod(0o755)
    if conf is not None:
        c = home.joinpath(*fork_lsfg.CONF_REL)
        c.parent.mkdir(parents=True)
        c.write_text(conf)
    return home


def _roms(tmp_path, *systems):
    roms = tmp_path / "roms"
    for s in systems:
        (roms / s).mkdir(parents=True)
        (roms / s / "game.bin").write_text("x")
    (roms / "empty").mkdir(parents=True)
    (roms / "empty" / "systeminfo.txt").write_text("x")
    return roms


def _launch(home, rom_path):
    env = {"HOME": str(home), "PATH": os.environ["PATH"]}
    out = subprocess.run(["bash", str(LAUNCHER), "echo", "RUN", rom_path], env=env, capture_output=True, text=True)
    return out.stdout.strip()


@pytest.mark.parametrize(
    ("conf", "system", "through_lsfg"),
    [
        (None, "pc98", True),
        ("*\n", "pc98", True),
        ("* -pc98\n", "pc98", False),
        ("* -pc98\n", "snes", True),
        ("-pc98 *  # comment\n", "pc98", False),
        ("snes ps2\n", "pc98", False),
        ("snes ps2\n", "snes", True),
        ("", "snes", False),
    ],
)
def test_launcher_rule_matches_status(tmp_path, conf, system, through_lsfg):
    home = _home(tmp_path, conf)
    out = _launch(home, f"/home/deck/retrodeck/roms/{system}/game.hdi")
    assert out.startswith("LSFG") is through_lsfg
    assert fork_lsfg.enabled_for(fork_lsfg._tokens(str(home)), system) is through_lsfg


def test_status_lists_installed_systems(tmp_path):
    home = _home(tmp_path, "* -pc98\n")
    roms = _roms(tmp_path, "snes", "pc98")
    st = fork_lsfg.status(str(home), str(roms))
    assert st == {
        "available": True,
        "all": True,
        "systems": [{"name": "pc98", "enabled": False}, {"name": "snes", "enabled": True}],
    }


def test_status_without_lsfg_script(tmp_path):
    home = _home(tmp_path, script=False)
    assert fork_lsfg.status(str(home), str(tmp_path / "nope")) == {"available": False, "all": True, "systems": []}


def test_turning_one_off_then_on_from_no_file(tmp_path):
    home = _home(tmp_path)
    assert fork_lsfg.set_system(str(home), "pc98", False) == {"success": True, "enabled": False}
    assert fork_lsfg._tokens(str(home)) == ["*", "-pc98"]
    assert _launch(home, "/x/roms/pc98/g.hdi") == "RUN /x/roms/pc98/g.hdi"
    assert _launch(home, "/x/roms/snes/g.sfc").startswith("LSFG")
    assert fork_lsfg.set_system(str(home), "pc98", True) == {"success": True, "enabled": True}
    assert fork_lsfg._tokens(str(home)) == ["*"]


def test_explicit_list_adds_and_drops_names(tmp_path):
    home = _home(tmp_path, "snes ps2 # mine\n")
    fork_lsfg.set_system(str(home), "pc98", True)
    fork_lsfg.set_system(str(home), "snes", False)
    assert fork_lsfg._tokens(str(home)) == ["ps2", "pc98"]


@pytest.mark.parametrize("bad", ["", "../x", "a b", "PC98", "-pc98", None])
def test_rejects_bad_names(tmp_path, bad):
    home = _home(tmp_path)
    assert fork_lsfg.set_system(str(home), bad, False)["reason"] == "bad_system"
    assert not home.joinpath(*fork_lsfg.CONF_REL).exists()
