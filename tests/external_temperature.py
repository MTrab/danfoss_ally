"""Shared fixtures for the invalid external temperature marker (#427)."""

from __future__ import annotations

import pytest
from pydanfossally import parse_device_data

# Raw payload of a radiator thermostat that never had an external room sensor:
# ext_measured_rs carries the Zigbee int16 invalid marker (0x8000), see #427.
INVALID_EXTERNAL_TEMPERATURE_PAYLOAD = {
    "id": "device-1",
    "name": "Living room",
    "status": [
        {"code": "temp_current", "value": 209},
        {"code": "ext_measured_rs", "value": -32768},
    ],
}

# Normalizing the marker is the library's job (MTrab/pydanfossally#62).
requires_invalid_marker_fix = pytest.mark.skipif(
    parse_device_data(INVALID_EXTERNAL_TEMPERATURE_PAYLOAD)["ext_measured_rs"] != -80.0,
    reason="needs a pydanfossally release that maps the 0x8000 marker to -80.0",
)
