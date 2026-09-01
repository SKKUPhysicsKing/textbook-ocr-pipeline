from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class PreprocessConfig:
    max_width: int = 2400
    denoise: bool = True
    autocontrast: bool = True
    threshold: int | None = None
    deskew: bool = True
    max_skew_degrees: float = 4.0
    skew_step: float = 0.5


def _otsu_threshold(gray: Image.Image) -> int:
    histogram = np.asarray(gray.histogram(), dtype=np.float64)
    total = histogram.sum()
    if total == 0:
        return 127
    indices = np.arange(256, dtype=np.float64)
    total_mean = float(np.dot(indices, histogram))
    background_weight = 0.0
    background_sum = 0.0
    best_variance = -1.0
    best_threshold = 127
    for value in range(256):
        background_weight += histogram[value]
        if background_weight == 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break
        background_sum += value * histogram[value]
        background_mean = background_sum / background_weight
        foreground_mean = (total_mean - background_sum) / foreground_weight
        variance = background_weight * foreground_weight * (background_mean - foreground_mean) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = value
    return best_threshold


def _projection_score(binary: Image.Image, angle: float) -> float:
    rotated = binary.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False, fillcolor=255)
    ink = 255.0 - np.asarray(rotated, dtype=np.float32)
    rows = ink.sum(axis=1)
    return float(np.square(np.diff(rows)).sum())


def estimate_skew(binary: Image.Image, max_degrees: float = 4.0, step: float = 0.5) -> float:
    if max_degrees <= 0 or step <= 0:
        return 0.0
    preview = binary.copy()
    if preview.width > 1000:
        ratio = 1000 / preview.width
        preview = preview.resize((1000, max(1, round(preview.height * ratio))), Image.Resampling.BILINEAR)
    angles = np.arange(-max_degrees, max_degrees + step / 2, step)
    scores = [_projection_score(preview, float(angle)) for angle in angles]
    return float(angles[int(np.argmax(scores))])


def preprocess_image(image: Image.Image, config: PreprocessConfig | None = None) -> Image.Image:
    config = config or PreprocessConfig()
    image = ImageOps.exif_transpose(image).convert("L")
    if config.max_width > 0 and image.width > config.max_width:
        ratio = config.max_width / image.width
        image = image.resize((config.max_width, max(1, round(image.height * ratio))), Image.Resampling.LANCZOS)
    if config.denoise:
        image = image.filter(ImageFilter.MedianFilter(size=3))
    if config.autocontrast:
        image = ImageOps.autocontrast(image, cutoff=1)
    threshold = config.threshold if config.threshold is not None else _otsu_threshold(image)
    binary = image.point(lambda pixel: 255 if pixel > threshold else 0, mode="1").convert("L")
    if config.deskew:
        angle = estimate_skew(binary, max_degrees=config.max_skew_degrees, step=config.skew_step)
        if abs(angle) >= config.skew_step / 2:
            binary = binary.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255)
    return binary

