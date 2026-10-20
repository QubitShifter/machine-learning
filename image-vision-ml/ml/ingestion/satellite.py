
"""
Image Vision ML
Phase 2: First Sentinel-2 satellite ingestion.

Search Earth Search STAC for a Sentinel-2 L2A scene,
read a small geographical window, and save:
- Red band (B04)
- NIR band (B08)
- NDVI GeoTIFF
- NDVI PNG preview
- Scene metadata JSON

The NDVI in this introductory example is calculated
from stored band values. Radiometric offsets must be
handled before using it as a calibrated scientific product.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio

from matplotlib.colors import Normalize
from pystac_client import Client
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds, transform

from ml.ingestion.stac import search_sentinel2


# --------------------------------------------------
# Configuration
# --------------------------------------------------

STAC_URL = "https://earth-search.aws.element84.com/v1"

COLLECTION = "sentinel-2-l2a"

# Small area south of Plovdiv, Bulgaria.
# Format: west, south, east, north (EPSG:4326)
BBOX = (
    24.65,
    42.05,
    24.68,
    42.08,
)

DATE_RANGE = "2025-06-01/2025-09-30"

MAX_CLOUD_COVER = 20

OUTPUT_DIR = Path("data/raw/satellite/first_image")


# --------------------------------------------------
# Search satellite catalog
# --------------------------------------------------

def search_satellite_image():
    print("Connecting to Earth Search STAC API...")

    client = Client.open(STAC_URL)

    search = client.search(
        collections=[COLLECTION],
        bbox=BBOX,
        datetime=DATE_RANGE,
        query={
            "eo:cloud_cover": {
                "lt": MAX_CLOUD_COVER
            }
        },
        max_items=100,
    )

    items = list(search.items())

    if not items:
        raise RuntimeError(
            "No satellite images found. "
            "Try a wider date range or cloud limit."
        )

    # Select lowest scene-level cloud coverage.
    items.sort(
        key=lambda item: item.properties.get(
            "eo:cloud_cover", 100
        )
    )

    item = items[0]

    print(f"Selected scene: {item.id}")
    print(f"Acquisition date: {item.datetime}")
    print(
        "Scene cloud cover: "
        f"{item.properties.get('eo:cloud_cover')}%"
    )

    return item


# --------------------------------------------------
# Read a geographical window from a COG
# --------------------------------------------------

def read_band(item, asset_name):
    if asset_name not in item.assets:
        raise KeyError(
            f"Asset '{asset_name}' not found. "
            f"Available: {list(item.assets)}"
        )

    url = item.assets[asset_name].href

    print(f"Reading {asset_name} band...")

    with rasterio.open(url) as src:

        # Transform WGS84 bounding box into
        # the image's native coordinate system.
        bounds = transform_bounds(
            "EPSG:4326",
            src.crs,
            *BBOX,
        )

        window = from_bounds(
            *bounds,
            transform=src.transform,
        )

        # Align to full pixels.
        window = window.round_offsets().round_lengths()

        data = src.read(1, window=window)

        if data.size == 0:
            raise RuntimeError(
                f"Empty raster window for {asset_name}"
            )

        profile = src.profile.copy()

        profile.update(
            height=data.shape[0],
            width=data.shape[1],
            transform=transform(
                window,
                src.transform,
            ),
            count=1,
        )

        return data, profile


# --------------------------------------------------
# Save GeoTIFF
# --------------------------------------------------

def save_geotiff(filename, data, profile):
    output_profile = profile.copy()

    output_profile.update(
        driver="GTiff",
        dtype=str(data.dtype),
        count=1,
        compress="deflate",
    )

    with rasterio.open(
        filename,
        "w",
        **output_profile,
    ) as dst:
        dst.write(data, 1)

    print(f"Saved: {filename}")


# --------------------------------------------------
# Calculate NDVI
# --------------------------------------------------

def calculate_ndvi(red, nir):
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)

    denominator = nir + red

    ndvi = np.full(
        red.shape,
        np.nan,
        dtype=np.float32,
    )

    valid = (
        (red > 0)
        & (nir > 0)
        & (denominator > 0)
    )

    np.divide(
        nir - red,
        denominator,
        out=ndvi,
        where=valid,
    )

    return ndvi


# --------------------------------------------------
# Create NDVI preview
# --------------------------------------------------

def save_ndvi_preview(ndvi, filename):
    fig, ax = plt.subplots(figsize=(10, 8))

    image = ax.imshow(
        ndvi,
        cmap="RdYlGn",
        norm=Normalize(vmin=-1, vmax=1),
    )

    ax.set_title(
        "Sentinel-2 NDVI - Plovdiv, Bulgaria"
    )

    ax.set_axis_off()

    fig.colorbar(
        image,
        ax=ax,
        label="NDVI",
        shrink=0.8,
    )

    fig.savefig(
        filename,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(f"Saved preview: {filename}")


# --------------------------------------------------
# Main execution
# --------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    item = search_satellite_image()

    red, red_profile = read_band(item, "red")
    nir, nir_profile = read_band(item, "nir")

    if (
        red.shape != nir.shape
        or red_profile["crs"] != nir_profile["crs"]
        or not red_profile["transform"].almost_equals(
            nir_profile["transform"]
        )
    ):
        raise RuntimeError(
            "Red and NIR rasters are not aligned."
        )

    print(f"Image dimensions: {red.shape}")

    save_geotiff(
        OUTPUT_DIR / "red_B04.tif",
        red,
        red_profile,
    )

    save_geotiff(
        OUTPUT_DIR / "nir_B08.tif",
        nir,
        nir_profile,
    )

    ndvi = calculate_ndvi(red, nir)

    ndvi_profile = red_profile.copy()
    ndvi_profile.update(
        dtype="float32",
        nodata=np.nan,
    )

    save_geotiff(
        OUTPUT_DIR / "ndvi.tif",
        ndvi,
        ndvi_profile,
    )

    save_ndvi_preview(
        ndvi,
        OUTPUT_DIR / "ndvi_preview.png",
    )

    metadata = {
        "scene_id": item.id,
        "acquisition_date": item.datetime.isoformat(),
        "cloud_cover": item.properties.get(
            "eo:cloud_cover"
        ),
        "bbox": list(BBOX),
        "collection": COLLECTION,
        "stac_url": STAC_URL,
        "assets": {
            "red": item.assets["red"].href,
            "nir": item.assets["nir"].href,
        },
        "ndvi_processing": (
            "Exploratory raw-value NDVI; "
            "no scene classification mask "
            "or radiometric offset correction."
        ),
    }

    metadata_file = OUTPUT_DIR / "metadata.json"

    metadata_file.write_text(
        json.dumps(
            metadata,
            indent=4,
        ),
        encoding="utf-8",
    )

    valid_values = ndvi[np.isfinite(ndvi)]

    if valid_values.size:
        print(
            f"NDVI min: {valid_values.min():.4f}"
        )
        print(
            f"NDVI max: {valid_values.max():.4f}"
        )
        print(
            f"NDVI mean: {valid_values.mean():.4f}"
        )
    else:
        print("No valid NDVI pixels found.")

    print()
    print("Satellite image ingestion complete.")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
