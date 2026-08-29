"""Compatibility seam for future Pipecat realtime voice pipelines."""

from collections.abc import Sequence

from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameProcessor


def create_realtime_pipeline(processors: Sequence[FrameProcessor]) -> Pipeline:
    """Create a Pipecat core pipeline from caller-supplied processors."""
    return Pipeline(processors)
