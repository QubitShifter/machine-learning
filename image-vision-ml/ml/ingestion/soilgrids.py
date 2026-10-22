"""ISRIC SoilGrids import contract.

The SoilGrids REST API is reported paused. This adapter does not fabricate
properties and does not contact the network unless explicitly requested.
"""

from __future__ import annotations

from typing import Any

from ml.sources.registry import get_source


SOILGRIDS_REST_STATUS = "paused"
CANDIDATE_PROPERTIES = (
    "sand",
    "clay",
    "silt",
    "bdod",
    "soc",
    "cfvo",
    "phh2o",
    "soil_depth",
)


def soilgrids_availability(*, allow_network: bool = False) -> dict[str, Any]:
    record = get_source("isric_soilgrids") or {}
    return {
        "source_id": "isric_soilgrids",
        "rest_api_status": SOILGRIDS_REST_STATUS,
        "allow_network": bool(allow_network),
        "network_executed": False,
        "properties_available": False,
        "field_capacity": None,
        "wilting_point": None,
        "plant_available_water_status": "not_estimated",
        "reason": (
            "SoilGrids REST v2.0 is paused. Properties are not fabricated. "
            "Official downloads, WMS/WCS, or WebDAV must be configured before ingestion."
        ),
        "official_url": record.get("official_source_url") or "https://isric.org/explore/soilgrids/",
        "candidate_properties": list(CANDIDATE_PROPERTIES),
        "integration_status": record.get("integration_status", "paused"),
    }


def import_soilgrids_properties(*_args, **_kwargs) -> dict[str, Any]:
    """Placeholder import. Always returns not_available without live access."""
    availability = soilgrids_availability(allow_network=False)
    availability["status"] = "not_available"
    availability["records"] = []
    return availability
