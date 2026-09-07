"""Adapter for the `ImageTextReader` port, backed by Apple's Vision framework.

macOS only: `Vision.VNRecognizeTextRequest` runs on-device, on the machine
this process is running on, which is the whole point (no image ever leaves it).
"""

from __future__ import annotations

from typing import Any

import Vision
from Foundation import NSData


class AppleVisionTextReader:
    """Runs on-device OCR through Vision at the accurate recognition level."""

    def read_text(self, image_png: bytes) -> str:
        data = NSData.dataWithBytes_length_(image_png, len(image_png))
        handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)

        success, error = handler.performRequests_error_([request], None)
        if not success:
            raise RuntimeError(f"Vision text request failed: {error}")

        observations = request.results() or []
        return "\n".join(self._reading_order(observations))

    def _reading_order(self, observations: list[Any]) -> list[str]:
        """Top to bottom, left to right, by each observation's own bounding box.

        Vision does not promise its results in reading order, only in
        whatever order its internal detector produced them.
        """

        def sort_key(observation: Any) -> tuple[float, float]:
            box = observation.boundingBox()
            top = box.origin.y + box.size.height
            return (-top, box.origin.x)

        ordered = sorted(observations, key=sort_key)
        return [obs.topCandidates_(1)[0].string() for obs in ordered if obs.topCandidates_(1)]
