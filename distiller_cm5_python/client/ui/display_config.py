"""
E-Ink display configuration for Raspberry Pi.
"""

config = {
    "display": {
        # Core E-Ink Settings
        "eink_enabled": True,
        "width": 240,
        "height": 416,
        # Performance Settings
        "eink_refresh_interval": 1000,  # Milliseconds between captures
        "eink_adaptive_capture": True,  # Automatically adjust refresh rate based on activity
        "eink_full_refresh_interval": 30,  # Full refresh every N frames
        "eink_timer_based_mode": False,  # Use timer-based capture (False = event-driven mode)
        # Image Processing Settings - Optimized for UI content
        "eink_threshold": 128,  # Black/white threshold (0-255)
        "eink_bw_conversion": {
            "use_gamma": True,  # Apply gamma correction for better E-Ink contrast
            "gamma_value": 0.8,  # (0.7-0.9 recommended)
        },
        # Hardware Settings
        "Full_Refresh_LUT_MODE": True,  # Use full refresh LUT mode for better quality
        # Debug Settings
        "eink_save_capture": True,  # Save screen captures for debugging
        # UI Settings
        "dark_mode": False,
        "show_system_stats": True,
        "font": {
            "primary_font": "fonts/MartianMonoNerdFont-CondensedBold.ttf",
            "font_size_small": 12,
            "font_size_normal": 14,
            "font_size_medium": 16,
            "font_size_large": 18,
            "font_size_xlarge": 20,
        },

        # Flip screen orientation
        "flip_screen": True,
    }
}
