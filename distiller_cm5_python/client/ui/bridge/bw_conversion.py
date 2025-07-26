import numpy as np
import logging

# Try to import numba for optimization
try:
    from numba import jit

    NUMBA_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("Numba available: Using optimized BW conversion functions")
except ImportError:
    NUMBA_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Numba not available: Using standard BW conversion functions")

    # Create dummy decorator for when numba is not available
    def jit(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


@jit(nopython=True, cache=True)
def apply_gamma_correction(pixels, gamma_value):
    """
    Apply gamma correction to grayscale image for better E-Ink contrast.

    Args:
        pixels: Numpy array of grayscale image (0-255)
        gamma_value: Gamma value to apply (typically 0.7-0.9 for E-Ink)

    Returns:
        Numpy array with gamma correction applied
    """
    # Scale to 0-1, apply gamma, scale back to 0-255
    corrected = ((pixels / 255.0) ** gamma_value) * 255.0
    return corrected


@jit(nopython=True, cache=True)
def floyd_steinberg_dither(pixels, threshold=128):
    """
    Apply Floyd-Steinberg dithering for optimal E-Ink conversion.
    This is the best method for UI content with text and graphics.

    Args:
        pixels: Numpy array of grayscale image (0-255)
        threshold: Threshold for black/white conversion (0-255)

    Returns:
        Binary numpy array (values True=white, False=black)
    """
    height, width = pixels.shape
    dithered = pixels.astype(np.float32)

    # Process all rows except the last one
    for y in range(height - 1):
        for x in range(1, width - 1):
            old_pixel = dithered[y, x]
            new_pixel = 255.0 if old_pixel >= threshold else 0.0
            dithered[y, x] = new_pixel

            quant_error = old_pixel - new_pixel

            # Distribute error to neighboring pixels (Floyd-Steinberg weights)
            dithered[y, x + 1] += quant_error * 7.0 / 16.0
            dithered[y + 1, x - 1] += quant_error * 3.0 / 16.0
            dithered[y + 1, x] += quant_error * 5.0 / 16.0
            dithered[y + 1, x + 1] += quant_error * 1.0 / 16.0

    # Handle the last row separately (no pixels below to distribute error to)
    y = height - 1
    for x in range(1, width - 1):
        old_pixel = dithered[y, x]
        new_pixel = 255.0 if old_pixel >= threshold else 0.0
        dithered[y, x] = new_pixel

        quant_error = old_pixel - new_pixel
        dithered[y, x + 1] += quant_error * 7.0 / 16.0

    # Convert to boolean array (True=white, False=black)
    return dithered >= threshold


def convert_to_bw(pixels, config):
    """
    Convert a grayscale image to black and white using optimal E-Ink method.
    Uses gamma correction + Floyd-Steinberg dithering for best UI results.

    Args:
        pixels: Numpy array of grayscale image (0-255)
        config: Dictionary containing conversion parameters from display_config

    Returns:
        Binary numpy array (values True=white, False=black)
    """
    # Get configuration settings
    bw_config = config.get("eink_bw_conversion", {})
    use_gamma = bw_config.get("use_gamma", True)  # Default to True for better E-Ink contrast
    gamma_value = bw_config.get("gamma_value", 0.8)  # Optimized for E-Ink UI content
    threshold = config.get("eink_threshold", 128)

    # Make sure we're working with a copy
    pixels = pixels.copy().astype(np.float32)

    # Apply gamma correction for better E-Ink contrast
    if use_gamma:
        pixels = apply_gamma_correction(pixels, gamma_value)

    # Apply Floyd-Steinberg dithering for optimal E-Ink results
    return floyd_steinberg_dither(pixels, threshold)


# Simplified conversion function for direct use
def convert_grayscale_to_1bit(pixels, gamma=0.8, threshold=128, dithering=True):
    """
    Direct conversion function for grayscale to 1-bit E-Ink format.

    Args:
        pixels: Numpy array of grayscale image (0-255)
        gamma: Gamma correction value (0.7-0.9 recommended for E-Ink)
        threshold: Black/white threshold (0-255)
        dithering: Whether to apply Floyd-Steinberg dithering

    Returns:
        Binary numpy array (True=white, False=black)
    """
    pixels = pixels.astype(np.float32)

    # Apply gamma correction
    pixels = apply_gamma_correction(pixels, gamma)

    if dithering:
        return floyd_steinberg_dither(pixels, threshold)
    else:
        # Simple threshold without dithering
        return pixels >= threshold
