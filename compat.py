"""
compat.py
=========
One import for the whole app: ``from compat import ctk``.

If CustomTkinter is installed (the normal case, see README.md) this module just
re-exports it, and the app looks modern.

If CustomTkinter is **not** installed, a small set of look-alike classes built
on the standard ``tkinter`` library is used instead, so the program still runs.
The stand-ins accept the same keyword arguments that the app passes
(``fg_color``, ``text_color``, ``corner_radius``, ...) and simply ignore the ones
plain Tk does not have.  The layout is the same, only the styling is simpler.

Nothing in this module is clever: it is a thin translation layer between the
CustomTkinter names and plain Tk widget options.
"""

import tkinter
from tkinter import ttk


# ============================================================================
# SECTION 1 - Which toolkit are we using?
# ============================================================================

try:
    import customtkinter as _customtkinter
    USING_CUSTOMTKINTER = True
    ctk = _customtkinter
except ImportError:                                    # CustomTkinter missing
    USING_CUSTOMTKINTER = False
    ctk = None          # filled in at the bottom of this file (class definitions)


# ============================================================================
# SECTION 2 - Stand-in widgets for plain Tkinter
# ============================================================================
# These classes are only *defined* when CustomTkinter is missing, so they add
# nothing to the normal code path.

def _build_fallback_module():
    """Create the namespace of stand-in widgets (used when CustomTkinter is missing)."""

    # -- helper: turn CustomTkinter names into plain Tk names ----------------

    def _background_of(widget):
        """Best guess at the background colour of any widget (never raises)."""
        try:
            colour = widget.cget("bg")
        except Exception:      # Tk widgets raise TclError, stand-ins TypeErrors
            return "#FFFFFF"
        return colour if isinstance(colour, str) and colour else "#FFFFFF"

    class _StyleMixin:
        """
        Translate the colour keywords used by the app into Tk keywords.

        Unknown keywords are ignored on purpose: the screens pass a few
        CustomTkinter-only options that plain Tk simply does not need.
        """

        _parent_background = None

        def _tk_options(self, **kwargs):
            # Work out the parent colour *before* Tk receives the widget, so
            # that "transparent" really means "same colour as the parent".
            if self._parent_background is None:
                self._parent_background = _background_of(self.master)
            options = {}
            fg = kwargs.pop("fg_color", None)
            bg = kwargs.pop("bg_color", None)
            text = kwargs.pop("text_color", None)
            hover = kwargs.pop("hover_color", None)

            # "transparent" means "use the parent's colour".
            def resolve(colour):
                if colour == "transparent":
                    return self._parent_background
                return colour

            # ttk widgets (used by the progress bar) take their colours from a
            # style, not from options like "bg" / "fg".
            is_ttk_widget = isinstance(self, ttk.Widget) and not isinstance(
                self, (tkinter.Tk, tkinter.Toplevel))

            if not is_ttk_widget:
                if fg is not None:
                    options["bg"] = resolve(fg)
                if bg is not None and "bg" not in options:
                    options["bg"] = resolve(bg)
                if text is not None:
                    options["fg"] = text
                if hover is not None:
                    options["activebackground"] = hover

            # Options that plain Tk understands as they are.
            for key in ("font", "text", "anchor", "justify", "wraplength", "command",
                        "state", "width", "height", "padx", "pady", "bd", "borderwidth"):

                if key in kwargs:
                    options[key] = kwargs.pop(key)

            return options

        def configure(self, **kwargs):
            options = self._tk_options(**kwargs)
            if options:
                super().configure(**options)

        config = configure

    # -- CTk (the main window) ----------------------------------------------
    class CTk(tkinter.Tk):
        def configure(self, **kwargs):
            options = {}
            if "fg_color" in kwargs:
                options["bg"] = kwargs.pop("fg_color")
            if options:
                super().configure(**options)

        config = configure

    class CTkToplevel(tkinter.Toplevel):
        def configure(self, **kwargs):
            options = {}
            if "fg_color" in kwargs:
                options["bg"] = kwargs.pop("fg_color")
            if options:
                super().configure(**options)

        config = configure

        def grab_set(self):
            """Plain Tk toplevels support this already; kept for clarity."""
            super().grab_set()

    # -- CTkFrame -----------------------------------------------------------
    class CTkFrame(_StyleMixin, tkinter.Frame):
        def __init__(self, master=None, **kwargs):
            options = self._tk_options(**kwargs)
            super().__init__(master, **options)

    # -- CTkLabel -----------------------------------------------------------
    class CTkLabel(_StyleMixin, tkinter.Label):
        def __init__(self, master=None, **kwargs):
            options = self._tk_options(**kwargs)
            super().__init__(master, **options)

    # -- CTkButton ----------------------------------------------------------
    class CTkButton(_StyleMixin, tkinter.Button):
        def __init__(self, master=None, **kwargs):
            options = self._tk_options(**kwargs)
            options.setdefault("state", "normal")
            options.setdefault("relief", "raised")
            super().__init__(master, **options)

        def configure(self, **kwargs):
            """Support the few CustomTkinter options the app changes at runtime."""
            options = self._tk_options(**kwargs)
            state = options.pop("state", None)
            if options:
                tkinter.Button.configure(self, **options)
            if state is not None:
                tkinter.Button.configure(self, state=state)

        config = configure

    # -- CTkEntry -----------------------------------------------------------
    class CTkEntry(_StyleMixin, tkinter.Entry):
        """Entry with the same tiny placeholder feature the app uses."""

        def __init__(self, master=None, **kwargs):
            self._placeholder_text = kwargs.pop("placeholder_text", "")
            self._placeholder_active = False
            options = self._tk_options(**kwargs)
            super().__init__(master, **options)
            self.bind("<FocusIn>", self._hide_placeholder)
            self.bind("<FocusOut>", self._show_placeholder)
            if self._placeholder_text:
                self._show_placeholder()

        def _show_placeholder(self, event=None):
            if not super().get():
                self._placeholder_active = True
                self.insert(0, self._placeholder_text)

        def _hide_placeholder(self, event=None):
            if self._placeholder_active:
                self._placeholder_active = False
                self.delete(0, "end")

        def get(self):
            """An empty box while the placeholder is showing is just empty."""
            return "" if self._placeholder_active else super().get()

        def delete(self, first, last=None):
            self._placeholder_active = False
            return super().delete(first, last)

    # -- CTkSlider ----------------------------------------------------------
    class CTkSlider(_StyleMixin, tkinter.Scale):
        def __init__(self, master=None, **kwargs):
            self._command = kwargs.pop("command", None)
            kwargs.pop("number_of_steps", None)
            self._from_value = kwargs.pop("from_", 0)
            self._to_value = kwargs.pop("to", 100)
            options = self._tk_options(**kwargs)
            options.pop("state", None)
            super().__init__(master, from_=self._from_value, to=self._to_value,
                             orient="horizontal", showvalue=False,
                             command=self._on_move, **options)

        def _on_move(self, value):
            if self._command:
                self._command(float(value))

        def set(self, value):
            """
            Set the slider position.

            CustomTkinter sliders work with 0-100 values here, so the value is
            simply written through.  (Values are clamped by the Scale widget.)
            """
            try:
                tkinter.Scale.set(self, float(value))
            except Exception:
                pass

        def get(self):
            try:
                return float(tkinter.Scale.get(self))
            except (tkinter.TclError, ValueError):
                return 0.0

    # -- CTkProgressBar -----------------------------------------------------
    class CTkProgressBar(tkinter.Frame):
        def __init__(self, master=None, **kwargs):
            kwargs.pop("corner_radius", None)
            kwargs.pop("border_width", None)
            self._fg = kwargs.pop("progress_color", None)
            self._bg = kwargs.pop("fg_color", None)
            kwargs.pop("bg_color", None)
            kwargs.pop("height", None)
            super().__init__(master, height=14)
            self._bar = ttk.Progressbar(self, maximum=100)
            self._bar.pack(fill="both", expand=True)

        def set(self, value):
            """value is 0.0 - 1.0 (the CustomTkinter convention)."""
            self._bar["value"] = max(0.0, min(1.0, float(value))) * 100

        def get(self):
            return self._bar["value"] / 100

        def configure(self, **kwargs):
            if "progress_color" in kwargs:
                self._fg = kwargs.pop("progress_color")
            if "fg_color" in kwargs:
                self._bg = kwargs.pop("fg_color")
            for key in list(kwargs):
                kwargs.pop(key)
            # Make the colours visible in the ttk style as well.
            style = ttk.Style(self)
            if self._fg:
                style.configure("HCI.Horizontal.TProgressbar", background=self._fg)
                self._bar.configure(style="HCI.Horizontal.TProgressbar")

        config = configure

    # -- CTkSegmentedButton -------------------------------------------------
    class CTkSegmentedButton(tkinter.Frame):
        """A row of radio-like buttons, behaving like CustomTkinter's widget."""

        def __init__(self, master=None, values=None, command=None, **kwargs):
            self._values = list(values or [])
            self._command = command
            self._variable = tkinter.StringVar(value=self._values[0] if self._values else "")
            self._buttons = {}

            fg = kwargs.pop("fg_color", None)
            bg = kwargs.pop("bg_color", None)
            text_color = kwargs.pop("text_color", None)
            selected = kwargs.pop("selected_color", None)
            unselected = kwargs.pop("unselected_color", None)
            font = kwargs.pop("font", None)

            super().__init__(master)
            if bg:
                super().configure(bg=bg)
            elif fg:
                super().configure(bg=fg)

            for column, value in enumerate(self._values):
                button = tkinter.Radiobutton(
                    self, text=value, value=value, variable=self._variable,
                    indicatoron=False, command=self._on_click,
                    font=font, fg=text_color, bg=unselected or bg,
                    selectcolor=selected or fg, activebackground=selected or fg,
                    bd=1, relief="raised", padx=6, pady=4)
                button.grid(row=0, column=column, sticky="ew")
                self.grid_columnconfigure(column, weight=1)
                self._buttons[value] = button

        def _on_click(self):
            if self._command:
                self._command(self._variable.get())

        def set(self, value):
            """Select a value without calling the command (like CustomTkinter)."""
            if value in self._buttons or not self._buttons:
                self._variable.set(value)

        def get(self):
            return self._variable.get()

        def configure(self, **kwargs):
            """Restyle the buttons (most options are simply ignored)."""
            text_color = kwargs.get("text_color")
            selected = kwargs.get("selected_color")
            unselected = kwargs.get("unselected_color")
            font = kwargs.get("font")
            for button in self._buttons.values():
                options = {}
                if text_color:
                    options["fg"] = text_color
                if selected:
                    options["selectcolor"] = selected
                    options["activebackground"] = selected
                if unselected:
                    options["bg"] = unselected
                if font:
                    options["font"] = font
                if options:
                    button.configure(**options)

        config = configure

    # -- module level functions ---------------------------------------------
    def set_appearance_mode(mode="light"):
        """Not needed for plain Tk; kept so main.py does not need an if."""

    namespace = {
        "CTk": CTk,
        "CTkToplevel": CTkToplevel,
        "CTkFrame": CTkFrame,
        "CTkLabel": CTkLabel,
        "CTkButton": CTkButton,
        "CTkEntry": CTkEntry,
        "CTkSlider": CTkSlider,
        "CTkProgressBar": CTkProgressBar,
        "CTkSegmentedButton": CTkSegmentedButton,
        "set_appearance_mode": set_appearance_mode,
    }
    return type("FallbackCustomTkinter", (), namespace)


# ============================================================================
# SECTION 3 - Build the fallback namespace when it is needed
# ============================================================================

if not USING_CUSTOMTKINTER:
    ctk = _build_fallback_module()
