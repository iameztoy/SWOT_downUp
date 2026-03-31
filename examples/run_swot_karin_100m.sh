#!/usr/bin/env bash
set -euo pipefail

CONFIG="configs/smoke_earthaccess_small_aoi.yaml"

# 1) Search granules
swot-pipeline search "$CONFIG"

# 2) Download locally
swot-pipeline download "$CONFIG"

# 3) Process NetCDF -> GeoTIFF/COG
swot-pipeline process "$CONFIG"

# 4) Publish (requires publish.enabled: true)
swot-pipeline publish "$CONFIG"

# Or run full chain in one command:
# swot-pipeline run-pipeline "$CONFIG"
