from __future__ import annotations

from pathlib import Path

from swot_pipeline.models import GranuleRecord, PipelineConfig, ProcessedRaster
from swot_pipeline.processing.extract import extract_variables
from swot_pipeline.processing.qa import apply_named_mask
from swot_pipeline.processing.raster_writer import write_multiband_raster
from swot_pipeline.processing.reader import open_dataset_lazy
from swot_pipeline.products.base import ProductPlugin


def process_granules(
    granules: list[GranuleRecord],
    config: PipelineConfig,
    plugin: ProductPlugin,
) -> list[ProcessedRaster]:
    outputs: list[ProcessedRaster] = []
    out_dir = config.process.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    bands = plugin.select_output_variables(config.process.variables, config.process.optional_variables)

    for granule in granules:
        if not granule.local_path:
            raise ValueError(f"Granule {granule.granule_id} is missing local_path; download step must run first")

        acquisition_time = plugin.parse_acquisition_time(granule)
        with open_dataset_lazy(granule.local_path) as ds:
            extracted = extract_variables(ds, plugin, bands, config.aoi)
            masks = plugin.build_quality_masks(extracted, config.process.quality_rules)

            arrays = dict(extracted)
            if config.process.include_qa_masks:
                arrays.update(masks)

            apply_mask = config.process.quality_rules.get("apply_mask")
            arrays = apply_named_mask(
                arrays,
                mask_name=apply_mask,
                masks=masks,
                skip_bands={"qa_keep_basic", "qa_keep_strict"},
            )

            out_name = f"{Path(granule.filename).stem}__{config.process.output_mode}.tif"
            out_path = write_multiband_raster(
                output_path=out_dir / out_name,
                ds=ds,
                arrays=arrays,
                plugin=plugin,
                config=config,
                acquisition_time=acquisition_time,
            )

        outputs.append(
            ProcessedRaster(
                source_granule=granule,
                local_path=out_path,
                bands=list(arrays.keys()),
                acquisition_time=acquisition_time,
                mode=config.process.output_mode,
                metadata={"quality_rules": config.process.quality_rules},
            )
        )

    return outputs
