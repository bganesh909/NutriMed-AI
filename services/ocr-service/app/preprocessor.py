"""Image preprocessing pipeline for optimal OCR accuracy.

Applies a sequence of transformations to clean up medical report images
before feeding them into PaddleOCR.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Target width for resizing (height scales proportionally)
TARGET_WIDTH = 2480  # ~A4 at 300 DPI


def preprocess(
    image: np.ndarray,
    *,
    target_width: int = TARGET_WIDTH,
    clahe_clip: float = 2.0,
    clahe_grid: int = 8,
    blur_kernel: int = 3,
    border_margin: int = 10,
) -> np.ndarray:
    """Run the full preprocessing pipeline and return the cleaned image.

    Parameters
    ----------
    image : np.ndarray
        Input image in BGR format (as read by cv2.imread).
    target_width : int
        Resize target width in pixels.
    clahe_clip : float
        CLAHE clip limit for contrast enhancement.
    clahe_grid : int
        CLAHE tile grid size.
    blur_kernel : int
        Kernel size for Gaussian blur (must be odd).
    border_margin : int
        Pixels to crop from each border.

    Returns
    -------
    np.ndarray
        Preprocessed grayscale image ready for OCR.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is empty or None")

    img = image.copy()

    # 1. Convert to grayscale
    img = to_grayscale(img)

    # 2. Remove borders
    img = remove_borders(img, margin=border_margin)

    # 3. Resize for optimal OCR
    img = resize_optimal(img, target_width=target_width)

    # 4. Noise removal
    img = remove_noise(img, kernel_size=blur_kernel)

    # 5. Contrast enhancement (CLAHE)
    img = enhance_contrast(img, clip_limit=clahe_clip, tile_grid_size=clahe_grid)

    # 6. Deskew
    img = deskew(img)

    # 7. Adaptive thresholding
    img = adaptive_threshold(img)

    return img


# ---------------------------------------------------------------------------
# Individual pipeline stages
# ---------------------------------------------------------------------------

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert an image to grayscale if it is not already."""
    if len(image.shape) == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if len(image.shape) == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return image


def remove_noise(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Apply Gaussian blur followed by bilateral filter for noise reduction."""
    kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
    blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    filtered = cv2.bilateralFilter(blurred, d=9, sigmaColor=75, sigmaSpace=75)
    return filtered


def adaptive_threshold(image: np.ndarray) -> np.ndarray:
    """Apply adaptive Gaussian thresholding to binarize the image."""
    return cv2.adaptiveThreshold(
        image,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=15,
        C=11,
    )


def deskew(image: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    """Detect and correct document skew using Hough line transform.

    Only corrects if the detected angle is within ``max_angle`` degrees.
    """
    # Edge detection
    edges = cv2.Canny(image, 50, 200, apertureSize=3)

    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180, threshold=100,
        minLineLength=image.shape[1] // 4, maxLineGap=20,
    )

    if lines is None:
        return image

    angles: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0:
            continue
        angle = math.degrees(math.atan2(dy, dx))
        # Only consider near-horizontal lines
        if abs(angle) < max_angle:
            angles.append(angle)

    if not angles:
        return image

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.3:
        # Too small to bother correcting
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    logger.debug("Deskewed image by %.2f degrees", median_angle)
    return rotated


def enhance_contrast(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: int = 8,
) -> np.ndarray:
    """Enhance local contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    clahe = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=(tile_grid_size, tile_grid_size),
    )
    return clahe.apply(image)


def remove_borders(image: np.ndarray, margin: int = 10) -> np.ndarray:
    """Remove a fixed margin from all sides to eliminate border artifacts.

    Also attempts to detect and remove solid borders via contour analysis.
    """
    h, w = image.shape[:2]
    if margin * 2 >= h or margin * 2 >= w:
        return image

    cropped = image[margin : h - margin, margin : w - margin]

    # Attempt to remove solid black/white borders using contour detection
    try:
        gray = cropped if len(cropped.shape) == 2 else to_grayscale(cropped)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area_ratio = cv2.contourArea(largest) / (gray.shape[0] * gray.shape[1])
            if 0.5 < area_ratio < 0.98:
                x, y, cw, ch = cv2.boundingRect(largest)
                pad = 5
                x = max(0, x - pad)
                y = max(0, y - pad)
                cw = min(cropped.shape[1] - x, cw + 2 * pad)
                ch = min(cropped.shape[0] - y, ch + 2 * pad)
                cropped = cropped[y : y + ch, x : x + cw]
    except Exception:
        logger.debug("Border contour removal skipped due to error", exc_info=True)

    return cropped


def resize_optimal(image: np.ndarray, target_width: int = TARGET_WIDTH) -> np.ndarray:
    """Resize image to target width while preserving aspect ratio.

    Only upscales if the image is smaller than target_width.
    """
    h, w = image.shape[:2]
    if w == 0:
        return image
    if w >= target_width:
        return image

    scale = target_width / w
    new_w = target_width
    new_h = int(h * scale)
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(image, (new_w, new_h), interpolation=interpolation)
