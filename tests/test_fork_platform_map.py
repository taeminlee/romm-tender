"""Fork addition (0.33.1-msu7): RomM slugs that ES-DE knows under another name reach the right system.

Without these, ``resolve_system`` handed back the RomM slug itself (``pc-9800-series``), so the
game landed in ``roms/pc-9800-series`` and no ES-DE system or core matched it.
"""

import json
import os

import pytest

CONFIG = os.path.join(os.path.dirname(__file__), "..", "defaults", "config.json")


@pytest.mark.parametrize(
    ("slug", "system"),
    [
        ("pc-9800-series", "pc98"),
        ("pc-8800-series", "pc88"),
        ("sharp-x68000", "x68000"),
        ("fm-towns", "fmtowns"),
        ("wonderswan-color", "wonderswancolor"),
        ("neogeoaes", "neogeo"),
    ],
)
def test_romm_slug_maps_to_es_de_system(slug, system):
    with open(CONFIG, encoding="utf-8") as f:
        assert json.load(f)["platform_map"][slug] == system
