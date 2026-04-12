"""
Terminal figures and Unicode glyphs
"""

import platform

_is_macos = platform.system() == "Darwin"

BLACK_CIRCLE = "⏺" if _is_macos else "●"
BULLET_OPERATOR = "∙"
TEARDROP_ASTERISK = "✻"
UP_ARROW = "↑"
DOWN_ARROW = "↓"
LIGHTNING_BOLT = "↯"
EFFORT_LOW = "○"
EFFORT_MEDIUM = "◐"
EFFORT_HIGH = "●"
EFFORT_MAX = "◉"

PLAY_ICON = "▶"
PAUSE_ICON = "⏸"

REFRESH_ARROW = "↻"
CHANNEL_ARROW = "←"
INJECTED_ARROW = "→"
FORK_GLYPH = "⑂"

DIAMOND_OPEN = "◇"
DIAMOND_FILLED = "◆"
REFERENCE_MARK = "※"

FLAG_ICON = "⚑"

BLOCKQUOTE_BAR = "▎"
HEAVY_HORIZONTAL = "━"

BRIDGE_SPINNER_FRAMES = ["·|·", "·/·", "·—·", "·\\·"]
BRIDGE_READY_INDICATOR = "·✓··"
BRIDGE_FAILED_INDICATOR = "×"
