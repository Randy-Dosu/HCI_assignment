"""
theme.py
========
The "visual variable" engine for the Human Perception & Performance Tester.

This module owns the three conditions the experimenter can change at any time:

    1. Contrast   High / Medium / Low   -> a colour palette for the whole UI
    2. Size       Small / Medium / Large-> the font sizes and shape sizes
    3. Brightness 0 - 100 %             -> every colour is scaled towards black

CustomTkinter widgets understand a small set of colour keywords (fg_color,
text_color, bg_color, ...).  Rather than setting those keywords in every single
task screen, the app *registers* each widget once with this module and gives it
a "role" (label, primary button, panel, ...).  When a condition changes we walk
over the registered widgets and restyle them.

That keeps the task code short, and it guarantees that "all three controls
restyle the whole interface immediately, including the task screens".
"""

import tkinter


# ============================================================================
# SECTION 1 - Settings the experimenter / student may want to change
# ============================================================================

CONTRAST_LEVELS = ["High", "Medium", "Low"]
SIZE_LEVELS = ["Small", "Medium", "Large"]

DEFAULT_CONTRAST = "Medium"
DEFAULT_SIZE = "Medium"
DEFAULT_BRIGHTNESS = 100          # percent

# Font family used everywhere.  "Helvetica" is a logical name that Tk maps to a
# sensible system font on Windows, macOS and Linux.
FONT_FAMILY = "Helvetica"

# Base font sizes in points, before the Size condition is applied.
FONT_BASE_SIZE = {
    "title": 24,      # screen titles
    "heading": 18,    # section headings
    "body": 14,       # normal text, buttons, entry boxes
    "small": 12,      # hints, status line
}

# Size condition -> font multiplier.  Small/Medium/Large therefore give roughly
# 11 / 14 / 18 pt body text and 19 / 24 / 31 pt titles.
FONT_SCALE = {"Small": 0.78, "Medium": 1.00, "Large": 1.30}

# Size condition -> multiplier for shapes and icons (figure, radio buttons,
# slider height, progress bar height).  Only sizes change, never positions.
SHAPE_SCALE = {"Small": 0.75, "Medium": 1.00, "Large": 1.30}

# Size condition -> width of the control panel on the left (pixels).
# The panel has to grow so that "Large" labels still fit on one line.
SIDEBAR_WIDTH = {"Small": 250, "Medium": 300, "Large": 360}

# How big the ambiguous figure is drawn, relative to its design size.
FIGURE_SCALE = {"Small": 0.60, "Medium": 0.80, "Large": 1.00}

# The slider knob keeps at least this brightness (%).  At 0 % brightness the
# whole screen turns black, and without this little floor the experimenter
# could never find the slider to turn the brightness back up.
KNOB_MIN_BRIGHTNESS = 15


# ---------------------------------------------------------------------------
# 1b. The three contrast palettes
# ---------------------------------------------------------------------------
# Each palette defines every colour the interface needs.  The comments give the
# approximate WCAG contrast ratio of the text against its background:
#   *  High   : black text on white                (21.0 : 1)
#   *  Medium : dark grey text on light grey       ( 5.1 : 1, still readable)
#   *  Low    : light grey text on light grey      ( 1.8 : 1, hard to read
#                                                   but not invisible)
CONTRAST_PALETTES = {
    "High": {
        "bg": "#FFFFFF",        # window / task canvas background
        "panel": "#FFFFFF",     # panels and cards
        "text": "#000000",      # main text and the ambiguous figure
        "muted": "#333333",     # hints and the status line
        "line": "#C9C9C9",      # subtle dividers and outlines
        "accent": "#1B4F9C",    # primary buttons / target
        "accent_hover": "#123A75",
        "on_accent": "#FFFFFF", # text drawn on top of an accent colour
    },
    "Medium": {
        "bg": "#E6E6E6",
        "panel": "#EDEDED",
        "text": "#5F5F5F",
        "muted": "#707070",
        "line": "#C4C4C4",
        "accent": "#68717C",
        "accent_hover": "#59616B",
        "on_accent": "#F5F5F5",
    },
    "Low": {
        "bg": "#CFCFCF",
        "panel": "#D6D6D6",
        "text": "#9C9EA0",
        "muted": "#ACACAC",
        "line": "#C4C4C4",
        "accent": "#8F8F8F",
        "accent_hover": "#878787",
        "on_accent": "#BDBDBD",
    },
}


# ============================================================================
# SECTION 2 - Small colour / font helper functions
# ============================================================================

def hex_to_rgb(hex_color):
    """Turn '#1B4F9C' into the tuple (27, 79, 156)."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    """Turn the tuple (27, 79, 156) back into '#1B4F9C'."""
    red, green, blue = (max(0, min(255, int(round(value)))) for value in rgb)
    return f"#{red:02X}{green:02X}{blue:02X}"


def scale_color(hex_color, factor):
    """
    Multiply a colour by `factor` (0.0 - 1.0).

    This is how the brightness slider works: every channel is scaled towards 0,
    so factor 1.0 keeps the colour and factor 0.0 turns it black.
    """
    factor = max(0.0, min(1.0, factor))
    red, green, blue = hex_to_rgb(hex_color)
    return rgb_to_hex((red * factor, green * factor, blue * factor))


def relative_luminance(hex_color):
    """WCAG relative luminance of a colour (0 = black, 1 = white)."""
    channels = []
    for value in hex_to_rgb(hex_color):
        value = value / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(color_a, color_b):
    """
    WCAG contrast ratio between two colours (1 : 1 up to 21 : 1).

    The app does not need this to run - it is a handy little helper to show that
    the three contrast modes really are different.  README.md lists the values.
    """
    luminance_a = relative_luminance(color_a)
    luminance_b = relative_luminance(color_b)
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def build_colors(contrast, brightness):
    """
    Combine the contrast palette with the brightness value.

    Returns a dictionary with the same keys as CONTRAST_PALETTES plus a "knob"
    colour for the slider handle.
    """
    palette = CONTRAST_PALETTES[contrast]
    factor = brightness / 100

    colors = {name: scale_color(value, factor) for name, value in palette.items()}

    # The slider knob never disappears completely (see KNOB_MIN_BRIGHTNESS).
    # When the screen is dark the knob is drawn light so that it stays visible.
    palette_knob = palette["text"]
    if relative_luminance(colors["bg"]) < 0.35:
        palette_knob = palette["bg"]
    knob_factor = max(factor, KNOB_MIN_BRIGHTNESS / 100)
    colors["knob"] = scale_color(palette_knob, knob_factor)
    return colors


# ============================================================================
# SECTION 3 - The Theme object
# ============================================================================

class Theme:
    """
    Holds the active visual condition and keeps every registered widget styled.

    Typical use inside a screen:

        self.theme.register(self.title_label, role="label", kind="title", bold=True)
        theme.font("body", bold=True)          # -> ("Helvetica", 14, "bold")
        theme.colors["text"]                   # -> current text colour
    """

    def __init__(self, root):
        self.root = root
        self.contrast = DEFAULT_CONTRAST
        self.size = DEFAULT_SIZE
        self.brightness = DEFAULT_BRIGHTNESS

        self.colors = build_colors(self.contrast, self.brightness)
        self._widgets = {}       # widget -> {"role": ..., "surface": ..., ...}
        self._listeners = []     # callbacks that run after every restyle

    # -- active condition --------------------------------------------------

    def condition_text(self):
        """The one-line summary shown at the top of the window."""
        return (f"Contrast: {self.contrast} | Size: {self.size} | "
                f"Brightness: {self.brightness}%")

    def snapshot(self):
        """
        Copy of the condition.  Task screens take a snapshot when a trial
        starts, so a trial is logged with the condition it was shown in, even
        if the experimenter moves a slider while the trial is running.
        """
        return {
            "contrast": self.contrast,
            "size": self.size,
            "brightness": self.brightness,
            "visual_condition": (f"Contrast={self.contrast}; Size={self.size}; "
                                 f"Brightness={self.brightness}"),
        }

    def set_contrast(self, value):
        """Called by the radio buttons in the control panel."""
        if value in CONTRAST_LEVELS and value != self.contrast:
            self.contrast = value
            self.apply()

    def set_size(self, value):
        """Called by the radio buttons in the control panel."""
        if value in SIZE_LEVELS and value != self.size:
            self.size = value
            self.apply()

    def set_brightness(self, value):
        """
        Called by the brightness slider (value is a float from 0 to 100).

        Anything that is not a number is ignored, and the value is kept inside
        the 0-100 range, so a bad value can never crash the interface.
        """
        try:
            value = int(round(float(value)))
        except (TypeError, ValueError):
            return
        value = max(0, min(100, value))
        if value != self.brightness:
            self.brightness = value
            self.apply()

    # -- fonts and sizes ---------------------------------------------------

    def font(self, kind="body", bold=False):
        """Return a Tk font tuple such as ('Helvetica', 14) or (..., 'bold')."""
        base = FONT_BASE_SIZE.get(kind, FONT_BASE_SIZE["body"])
        points = max(8, round(base * FONT_SCALE[self.size]))
        return (FONT_FAMILY, points, "bold") if bold else (FONT_FAMILY, points)

    def px(self, base_size):
        """Scale a shape size (radio button, slider, progress bar) by Size."""
        return max(8, round(base_size * SHAPE_SCALE[self.size]))

    def figure_scale(self):
        """How large the ambiguous figure is drawn under the current size."""
        return FIGURE_SCALE[self.size]

    def sidebar_width(self):
        """Width of the experimenter control panel in pixels."""
        return SIDEBAR_WIDTH[self.size]

    # -- widget registration ----------------------------------------------

    def register(self, widget, role="label", surface="panel", kind="body", bold=False):
        """
        Remember a widget so it can be restyled later.

        role    : how the widget is styled.  The available roles are:
                    "bg"        frame with the window background colour
                    "panel"     frame drawn as a card / panel
                    "container" invisible grouping frame (transparent)
                    "label"     normal text
                    "hint"      quieter grey text
                    "primary"   solid call-to-action button
                    "secondary" outlined, quieter button
                    "entry"     text input box
                    "slider"    the brightness slider
                    "progress"  the progress bar of the Fitts task
                    "custom"    the widget colours itself (segmented buttons)
        surface : which colour sits *behind* the widget ("panel" or "bg")
        kind    : font size group ("title", "heading", "body", "small")
        bold    : draw the text in bold
        """
        self._widgets[widget] = {
            "role": role,
            "surface": surface,
            "kind": kind,
            "bold": bold,
        }
        self._style_one(widget, self._widgets[widget])   # apply straight away
        return widget

    def add_listener(self, callback):
        """
        Run `callback(theme)` after every restyle.  The main window uses this to
        update the segmented buttons and the sidebar width.
        """
        self._listeners.append(callback)

    # -- restyling ---------------------------------------------------------

    def apply(self):
        """Recalculate the colours and restyle every registered widget."""
        self.colors = build_colors(self.contrast, self.brightness)

        try:
            self.root.configure(fg_color=self.colors["bg"])
        except tkinter.TclError:
            pass

        # Frames are restyled first, because CustomTkinter copies a frame's
        # colour onto its children.  Doing the children afterwards means the
        # more specific colour always wins.
        frame_roles = ("bg", "panel", "container")
        order = ([item for item in self._widgets.items() if item[1]["role"] in frame_roles]
                 + [item for item in self._widgets.items() if item[1]["role"] not in frame_roles])

        # A widget can be destroyed while it is registered (e.g. when the user
        # switches from one task screen to the other).  Forget those silently.
        dead_widgets = []
        for widget, meta in order:
            try:
                if not widget.winfo_exists():
                    dead_widgets.append(widget)
                    continue
                self._style_one(widget, meta)
            except tkinter.TclError:
                dead_widgets.append(widget)
        for widget in dead_widgets:
            self._widgets.pop(widget, None)

        # Let the window and the active task screen redraw their own details.
        for callback in self._listeners:
            callback(self)

    def _style_one(self, widget, meta):
        """
        Apply one role to one widget.

        A plain if/elif chain is used on purpose: it is easy to read and easy
        to extend for a student project.
        """
        colors = self.colors
        surface = colors[meta["surface"]]
        font = self.font(meta["kind"], meta["bold"])
        role = meta["role"]

        if role == "bg":
            # Frames that are part of the window background.
            widget.configure(fg_color=colors["bg"])

        elif role == "panel":
            # Frames that are drawn as cards / panels (rounded corners).
            # NOTE: CustomTkinter pushes a frame's colour onto its children, so
            # a "panel" frame must not be restyled after its children exist.
            widget.configure(fg_color=colors["panel"], corner_radius=10)

        elif role == "container":
            # A frame that only groups widgets without drawing a background.
            # The colour is transparent, so restyling it can never overwrite the
            # colours of its children (frames, labels, cards, ...).
            widget.configure(fg_color="transparent")

        elif role == "label":
            widget.configure(text_color=colors["text"], bg_color=surface, font=font)

        elif role == "hint":
            widget.configure(text_color=colors["muted"], bg_color=surface, font=font)

        elif role == "primary":
            # Solid "call to action" button.
            widget.configure(
                fg_color=colors["accent"],
                hover_color=colors["accent_hover"],
                text_color=colors["on_accent"],
                border_width=0,
                bg_color=surface,
                font=font,
            )

        elif role == "secondary":
            # Outlined, quieter button.
            widget.configure(
                fg_color=surface,
                hover_color=colors["line"],
                text_color=colors["text"],
                border_color=colors["muted"],
                border_width=2,
                bg_color=surface,
                font=font,
            )

        elif role == "entry":
            widget.configure(
                fg_color=surface,
                border_color=colors["muted"],
                text_color=colors["text"],
                placeholder_text_color=colors["muted"],
                bg_color=surface,
                font=font,
            )

        elif role == "slider":
            widget.configure(
                fg_color=colors["line"],
                progress_color=colors["text"],
                button_color=colors["knob"],
                button_hover_color=colors["text"],
                bg_color=surface,
                height=self.px(26),
            )

        elif role == "progress":
            widget.configure(
                fg_color=colors["line"],
                progress_color=colors["text"],
                bg_color=surface,
                height=self.px(16),
            )

        elif role == "custom":
            # The widget manages its own colours (e.g. the Fitts target).
            widget.configure(bg_color=surface)

        # Unknown roles are silently ignored - nothing breaks.
