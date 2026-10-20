"""Resolve Sentinel-2 reflectance scale and offset from documented provenance.

Earth Search COGs are not identical to ESA SAFE JP2 files. Some COGs
already have the Processing Baseline 04.00 BOA offset removed from
the stored digital numbers. In that case applying raster:bands
offset=-0.1 a second time is incorrect.

This module never invents coefficients from NDVI appearance or from
pixel-statistic heuristics. Ambiguous cases are flagged for review.
"""

from __future__ import annotations

from typing import Any


STATUS_VERIFIED = "verified"
STATUS_UNVERIFIED = "unverified"
STATUS_CONFLICTING = "conflicting"
STATUS_MISSING = "missing"

KNOWN_EARTH_SEARCH_SCALE = 0.0001


def resolve_stac_band_calibration(
    asset_fields: dict[str, Any],
    item_properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return the scale/offset that should be applied to stored COG pixels.

    reflectance = DN * scale + offset

    If ``earthsearch:boa_offset_applied`` is true, the stored DNs are
    already harmonized and the STAC raster offset must not be applied
    again. Scale is still taken from ``raster:bands``.
    """
    properties = item_properties or {}
    bands = asset_fields.get("raster:bands") or []
    band0 = bands[0] if bands else {}
    advertised_scale = band0.get("scale")
    advertised_offset = band0.get("offset")
    nodata = band0.get("nodata", 0)
    boa_applied = properties.get("earthsearch:boa_offset_applied")
    processing_baseline = properties.get("s2:processing_baseline")

    if advertised_scale is None:
        if boa_applied is None:
            raise ValueError(
                "STAC asset is missing raster:bands scale; "
                "reflectance cannot be calibrated."
            )
        # Earth Search documents 1e-4 as the optical scale when the
        # collection flag is present but raster:bands is incomplete.
        scale = KNOWN_EARTH_SEARCH_SCALE
        advertised_offset_value = (
            float(advertised_offset) if advertised_offset is not None else -0.1
        )
        notes = (
            "raster:bands.scale was missing. Used the documented Earth "
            "Search optical scale 0.0001 because earthsearch:boa_offset_applied "
            "is present. This remains unverified until raster:bands is complete."
        )
        if boa_applied is True:
            offset = 0.0
            source = "earthsearch:boa_offset_applied-missing-scale"
        else:
            offset = advertised_offset_value
            source = "stac-raster-bands-missing-scale"
        return _provenance(
            scale=scale,
            offset=offset,
            advertised_scale=None,
            advertised_offset=advertised_offset_value,
            nodata=nodata,
            boa_applied=boa_applied,
            processing_baseline=processing_baseline,
            source=source,
            validation_status=STATUS_UNVERIFIED,
            requires_review=True,
            notes=notes,
        )

    scale = float(advertised_scale)
    advertised_offset_value = (
        float(advertised_offset) if advertised_offset is not None else 0.0
    )

    if boa_applied is True:
        return _provenance(
            scale=scale,
            offset=0.0,
            advertised_scale=scale,
            advertised_offset=advertised_offset_value,
            nodata=nodata,
            boa_applied=boa_applied,
            processing_baseline=processing_baseline,
            source="earthsearch:boa_offset_applied",
            validation_status=STATUS_VERIFIED,
            requires_review=False,
            notes=(
                "COG digital numbers already include the BOA offset. "
                "Using raster:bands scale only."
            ),
        )
    if boa_applied is False:
        return _provenance(
            scale=scale,
            offset=advertised_offset_value,
            advertised_scale=scale,
            advertised_offset=advertised_offset_value,
            nodata=nodata,
            boa_applied=boa_applied,
            processing_baseline=processing_baseline,
            source="stac-raster-bands",
            validation_status=STATUS_VERIFIED,
            requires_review=False,
            notes="BOA offset is not pre-applied; using raster:bands scale and offset.",
        )
    return _provenance(
        scale=scale,
        offset=advertised_offset_value,
        advertised_scale=scale,
        advertised_offset=advertised_offset_value,
        nodata=nodata,
        boa_applied=boa_applied,
        processing_baseline=processing_baseline,
        source="stac-raster-bands-unverified",
        validation_status=STATUS_UNVERIFIED,
        requires_review=True,
        notes=(
            "earthsearch:boa_offset_applied is missing. "
            "Using raster:bands coefficients without independent confirmation."
        ),
    )


def refine_calibration_with_sample(
    digital_numbers,
    calibration: dict[str, Any],
    *,
    negative_fraction_limit: float = 0.40,
) -> dict[str, Any]:
    """Audit a pixel sample without changing documented coefficients.

    Negative surface reflectance can occur after atmospheric correction.
    A high negative fraction after applying a negative advertised offset
    is recorded as a discrepancy. Coefficients are never rewritten from
    image statistics.
    """
    import numpy as np

    from ml.preprocessing.features import to_reflectance

    updated = dict(calibration)
    scale = float(updated.get("scale", KNOWN_EARTH_SEARCH_SCALE))
    offset = float(updated.get("offset", 0.0))
    advertised_offset = updated.get("advertised_offset", offset)
    nodata = updated.get("nodata", 0)

    reflectance = to_reflectance(digital_numbers, scale, offset, nodata)
    finite = np.isfinite(reflectance)
    finite_count = int(finite.sum())
    if finite_count == 0:
        updated["negative_fraction"] = None
        updated["sample_finite_pixels"] = 0
        return updated

    negative_fraction = float(np.mean(reflectance[finite] < 0))
    updated["negative_fraction"] = negative_fraction
    updated["sample_finite_pixels"] = finite_count

    advertised = (
        None if advertised_offset is None else float(advertised_offset)
    )
    effective_differs = (
        advertised is not None and abs(advertised - offset) > 1e-12
    )
    high_negative = negative_fraction > negative_fraction_limit
    if high_negative and offset < 0:
        notes = list(_as_notes(updated.get("notes")))
        notes.append(
            "Effective negative offset produced "
            f"{negative_fraction:.0%} negative reflectance. "
            "Coefficients were not changed; the scene requires review."
        )
        updated["validation_status"] = STATUS_CONFLICTING
        updated["requires_review"] = True
        updated["discrepancy"] = "majority_negative_after_negative_offset"
        updated["notes"] = " ".join(notes)
        return updated

    if high_negative and effective_differs and advertised is not None and advertised < 0:
        notes = list(_as_notes(updated.get("notes")))
        notes.append(
            "Advertised negative offset would produce "
            f"{negative_fraction:.0%} negative reflectance if applied. "
            "The documented Earth Search flag already withheld that offset."
        )
        updated["discrepancy"] = "advertised_offset_conflicts_with_encoding"
        updated["notes"] = " ".join(notes)
        return updated

    return updated


def calibration_document_from_item(
    scene_id: str,
    item_properties: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    band_assets: dict[str, str],
) -> dict[str, Any]:
    """Build a local calibration.json payload from a STAC item."""
    bands: dict[str, Any] = {}
    shared: dict[str, Any] | None = None
    requires_review = False
    statuses: list[str] = []
    for band, asset_name in band_assets.items():
        if str(band).upper() == "SCL" or str(asset_name).lower() == "scl":
            continue
        asset = assets.get(asset_name)
        if not asset:
            continue
        resolved = resolve_stac_band_calibration(asset, item_properties)
        bands[band] = {
            "band": band,
            "scale": resolved["scale"],
            "offset": resolved["offset"],
            "advertised_scale": resolved.get("advertised_scale"),
            "advertised_offset": resolved["advertised_offset"],
            "source": resolved["source"],
            "validation_status": resolved["validation_status"],
            "requires_review": resolved["requires_review"],
        }
        requires_review = requires_review or bool(resolved["requires_review"])
        statuses.append(str(resolved["validation_status"]))
        shared = resolved

    validation_status = _combine_statuses(statuses) if statuses else STATUS_MISSING
    document: dict[str, Any] = {
        "source": (shared or {}).get("source", "stac"),
        "scene_id": scene_id,
        "boa_offset_applied": item_properties.get("earthsearch:boa_offset_applied"),
        "processing_baseline": item_properties.get("s2:processing_baseline"),
        "notes": (shared or {}).get("notes", ""),
        "validation_status": validation_status,
        "requires_review": requires_review or validation_status != STATUS_VERIFIED,
        "bands": bands,
    }
    return document


def summarize_calibration_status(document: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize calibration provenance for quality reports."""
    if not document:
        return {
            "validation_status": STATUS_MISSING,
            "requires_review": True,
            "source": None,
            "bands": {},
        }
    bands = {
        key: entry
        for key, entry in (document.get("bands") or {}).items()
        if str(key).upper() != "SCL" and isinstance(entry, dict)
    }
    statuses = [
        str(entry.get("validation_status") or STATUS_UNVERIFIED)
        for entry in bands.values()
    ]
    band_review = any(bool(entry.get("requires_review")) for entry in bands.values())
    status = _combine_statuses(statuses) if statuses else (
        document.get("validation_status") or STATUS_MISSING
    )
    requires_review = bool(
        band_review
        or status in {STATUS_UNVERIFIED, STATUS_CONFLICTING, STATUS_MISSING}
    )
    return {
        "validation_status": status,
        "requires_review": requires_review,
        "source": document.get("source"),
        "boa_offset_applied": document.get("boa_offset_applied"),
        "processing_baseline": document.get("processing_baseline"),
        "notes": document.get("notes"),
        "bands": bands,
    }


def _provenance(
    *,
    scale: float,
    offset: float,
    advertised_scale: float | None,
    advertised_offset: float,
    nodata: Any,
    boa_applied: Any,
    processing_baseline: Any,
    source: str,
    validation_status: str,
    requires_review: bool,
    notes: str,
) -> dict[str, Any]:
    return {
        "scale": scale,
        "offset": offset,
        "advertised_scale": advertised_scale,
        "advertised_offset": advertised_offset,
        "nodata": nodata,
        "boa_offset_applied": boa_applied,
        "processing_baseline": processing_baseline,
        "source": source,
        "validation_status": validation_status,
        "requires_review": requires_review,
        "notes": notes,
        "discrepancy": None,
    }


def _combine_statuses(statuses: list[str]) -> str:
    if not statuses:
        return STATUS_MISSING
    if STATUS_MISSING in statuses:
        return STATUS_MISSING
    if STATUS_CONFLICTING in statuses:
        return STATUS_CONFLICTING
    if STATUS_UNVERIFIED in statuses:
        return STATUS_UNVERIFIED
    return STATUS_VERIFIED


def _as_notes(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]
