"""
main.py
=======
Human Perception & Performance Tester - entry point and main window.

This window glues everything together:

  * the experimenter control panel (contrast, size, brightness),
  * the Participant ID field,
  * the menu that switches between the two task screens,
  * the "active condition" line at the top,
  * the status line that says when a result was saved.

Run it with:      python main.py
Install first:    pip install customtkinter
"""

import tkinter
from tkinter import messagebox

from compat import ctk

import logger
import tasks
import theme as theme_module


# ============================================================================
# SECTION 1 - Settings
# ============================================================================

APP_TITLE = "Human Perception & Performance Tester"
WINDOW_SIZE = (1240, 760)

# The minimum size is not arbitrary: with the widest control panel (Large) the
# Fitts canvas still gets about 700 px, which is enough for the Long distance.
MIN_WINDOW_SIZE = (1120, 700)

# Height of the strip at the top that shows the active visual condition.
CONDITION_BAR_HEIGHT = 52

# The visual condition itself (colours, font sizes, size multipliers) lives in
# theme.py; this module only builds the window around it.


# ============================================================================
# SECTION 2 - The main window
# ============================================================================

class App(ctk.CTk):
    """
    The main window.

    Layout
    ------
    +--------------------------------------------------------------+
    | Active condition: Contrast: High | Size: Medium | ...        |  <- always visible
    +---------------------+----------------------------------------+
    | Control panel       |  Start area  or  Task 1  or  Task 2    |
    | - Participant ID    |                                        |
    | - Contrast          |                                        |
    | - Size              |                                        |
    | - Brightness        |                                        |
    | - Tasks / buttons   |                                        |
    +---------------------+----------------------------------------+
    """

    def __init__(self):
        super().__init__()

        # -- appearance basics -------------------------------------------
        ctk.set_appearance_mode("light")
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.minsize(*MIN_WINDOW_SIZE)

        # -- the theme (contrast / size / brightness) ---------------------
        self.theme = theme_module.Theme(self)

        # -- window grid: condition bar on top, content underneath --------
        # Column 0 is the control panel (fixed width), column 1 the content
        # area that grows when the window is resized.
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self._build_condition_bar()
        self._build_content()
        self._build_sidebar()

        # Show the start screen and apply the colours once everything exists.
        self.theme.apply()
        self.show_start_screen()
        self.show_status(f"Ready. {self._csv_status()}")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------
    # Row 0: the always-visible "active condition" line
    # ------------------------------------------------------------------

    def _build_condition_bar(self):
        """A coloured strip at the top of the window with the active condition."""
        self.condition_bar = ctk.CTkFrame(self, corner_radius=0, height=CONDITION_BAR_HEIGHT)
        self.theme.register(self.condition_bar, role="panel")
        self.condition_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.condition_label = ctk.CTkLabel(
            self.condition_bar, text="", anchor="w")
        self.theme.register(self.condition_label, role="label", kind="heading", bold=True)
        self.condition_label.pack(side="left", padx=16, pady=10)

        self.csv_label = ctk.CTkLabel(self.condition_bar, text="", anchor="e")
        self.theme.register(self.csv_label, role="hint", kind="small")
        self.csv_label.pack(side="right", padx=16, pady=10)

        # The bar is the first thing that should update when a control moves.
        self.theme.add_listener(lambda theme: self._refresh_condition_bar())

    def _refresh_condition_bar(self):
        """Update the condition text and the results.csv hint."""
        self.condition_label.configure(text=f"Active condition:  {self.theme.condition_text()}")
        self.csv_label.configure(text=self._csv_status())

    def _csv_status(self):
        """Little hint in the top-right corner about the results file."""
        state = "appending to" if logger.csv_exists() else "will create"
        return f"Results file: results.csv ({state})"

    # ------------------------------------------------------------------
    # Row 1, column 1: the content area that swaps between screens
    # ------------------------------------------------------------------

    def _build_content(self):
        """The right-hand side: start screen, task 1 or task 2."""
        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.theme.register(self.content, role="bg")
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # -- status line at the very bottom of the content area --------------
        self.status_label = ctk.CTkLabel(self.content, text="", anchor="w")
        self.theme.register(self.status_label, role="hint", surface="bg", kind="small")
        self.status_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.current_screen = None
        self.current_task_name = None
        self.tasks = {}          # task name -> the screen object (kept alive)

        # -- the start screen ------------------------------------------------
        self.start_screen = ctk.CTkFrame(self.content, fg_color="transparent")
        self.theme.register(self.start_screen, role="bg")
        self.start_screen.grid_columnconfigure(0, weight=1)
        self.start_screen.grid_rowconfigure(3, weight=1)

        self.welcome_label = ctk.CTkLabel(
            self.start_screen, text="Welcome!", anchor="w")
        self.theme.register(self.welcome_label, role="label", surface="bg",
                            kind="title", bold=True)
        self.welcome_label.grid(row=0, column=0, sticky="w", padx=30, pady=(40, 6))

        self.welcome_text = ctk.CTkLabel(
            self.start_screen,
            text=("This program tests how visual conditions affect human perception and "
                  "performance.\n\n"
                  "How to run a session:\n"
                  "  1. Type the Participant ID in the panel on the left.\n"
                  "  2. Choose the task:  'Identification'  or  'Target Hitting'.\n"
                  "  3. Set Contrast, Size and Brightness (you can change them at any "
                  "time, even between trials).\n"
                  "  4. Read the instructions at the top of the task screen and follow "
                  "the buttons.\n\n"
                  "Every result is saved automatically to results.csv."),
            anchor="w", justify="left")
        self.theme.register(self.welcome_text, role="label", surface="bg", kind="body")
        self.welcome_text.grid(row=1, column=0, sticky="w", padx=30)

        self.start_hint = ctk.CTkLabel(
            self.start_screen, text="Use the two task buttons on the left to begin.",
            anchor="w")
        self.theme.register(self.start_hint, role="hint", surface="bg", kind="body")
        self.start_hint.grid(row=2, column=0, sticky="w", padx=30, pady=(18, 0))

    # ------------------------------------------------------------------
    # Row 1, column 0: the experimenter control panel
    # ------------------------------------------------------------------

    def _build_sidebar(self):
        """The control panel: participant ID, the three visual controls, tasks."""
        self.sidebar = ctk.CTkFrame(self, corner_radius=0)
        self.theme.register(self.sidebar, role="panel")
        self.sidebar.grid(row=1, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)

        controls = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.theme.register(controls, role="panel")
        controls.grid(row=0, column=0, sticky="new", padx=14, pady=14)
        controls.grid_columnconfigure(0, weight=1)

        row = 0

        def heading(text, parent=controls):
            """Small helper that adds a bold heading to the panel."""
            nonlocal row
            label = ctk.CTkLabel(parent, text=text, anchor="w")
            self.theme.register(label, role="label", kind="heading", bold=True)
            label.grid(row=row, column=0, sticky="ew", pady=(14 if row else 0, 4))
            row += 1
            return label

        def hint(text, parent=controls):
            """Small helper that adds a grey explanatory line to the panel."""
            nonlocal row
            label = ctk.CTkLabel(parent, text=text, anchor="w", justify="left", wraplength=260)
            self.theme.register(label, role="hint", kind="small")
            label.grid(row=row, column=0, sticky="ew", pady=(0, 6))
            row += 1
            return label

        # -- Participant ID ------------------------------------------------
        heading("Participant ID")
        self.participant_entry = ctk.CTkEntry(controls, placeholder_text="e.g. P01", height=38)
        self.theme.register(self.participant_entry, role="entry", surface="panel", kind="body")
        self.participant_entry.grid(row=row, column=0, sticky="ew")
        row += 1

        # -- Contrast ------------------------------------------------------
        heading("Contrast")
        self.contrast_menu = ctk.CTkSegmentedButton(
            controls, values=theme_module.CONTRAST_LEVELS, command=self.on_contrast_change)
        self.theme.register(self.contrast_menu, role="custom", surface="panel")
        self._style_segmented_button(self.contrast_menu)
        self.contrast_menu.set(theme_module.DEFAULT_CONTRAST)
        self.contrast_menu.grid(row=row, column=0, sticky="ew")
        row += 1
        hint("High = black on white, Low = light grey on light grey.")

        # -- Size ----------------------------------------------------------
        heading("Size")
        self.size_menu = ctk.CTkSegmentedButton(
            controls, values=theme_module.SIZE_LEVELS, command=self.on_size_change)
        self.theme.register(self.size_menu, role="custom", surface="panel")
        self._style_segmented_button(self.size_menu)
        self.size_menu.set(theme_module.DEFAULT_SIZE)
        self.size_menu.grid(row=row, column=0, sticky="ew")
        row += 1
        hint("Changes font sizes and shape sizes across every screen.")

        # -- Brightness ----------------------------------------------------
        heading("Brightness")
        self.brightness_value_label = ctk.CTkLabel(controls, text="100 %", anchor="e")
        self.theme.register(self.brightness_value_label, role="label", surface="panel",
                            kind="body", bold=True)
        self.brightness_value_label.grid(row=row, column=0, sticky="ew")
        row += 1

        self.brightness_slider = ctk.CTkSlider(
            controls, from_=0, to=100, number_of_steps=100, command=self.on_brightness_change)
        self.theme.register(self.brightness_slider, role="slider", surface="panel")
        self.brightness_slider.set(theme_module.DEFAULT_BRIGHTNESS)
        self.brightness_slider.grid(row=row, column=0, sticky="ew")
        row += 1
        hint("0 % = black screen, 100 % = normal. The knob stays visible so you can "
             "always slide back up.")

        # -- Tasks ---------------------------------------------------------
        heading("Task")
        self.identification_button = ctk.CTkButton(
            controls, text="Identification", height=46, command=self.open_identification)
        self.theme.register(self.identification_button, role="primary", surface="panel",
                            kind="body", bold=True)
        self.identification_button.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1

        self.hitting_button = ctk.CTkButton(
            controls, text="Target Hitting", height=46, command=self.open_target_hitting)
        self.theme.register(self.hitting_button, role="primary", surface="panel",
                            kind="body", bold=True)
        self.hitting_button.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1

        self.home_button = ctk.CTkButton(
            controls, text="Start screen", height=38, command=self.show_start_screen)
        self.theme.register(self.home_button, role="secondary", surface="panel",
                            kind="small", bold=False)
        self.home_button.grid(row=row, column=0, sticky="ew")
        row += 1

        # Apply the starting width and keep it correct after every restyle.
        self.sidebar.configure(width=self.theme.sidebar_width(),
                               height=WINDOW_SIZE[1] - CONDITION_BAR_HEIGHT)

        # Restyle the extras that are not plain roles: the two segmented
        # buttons, the sidebar width and the task screens.
        self.theme.add_listener(self._on_theme_applied)

    def _style_segmented_button(self, segmented_button):
        """
        Give a segmented button the colours and font of the current theme.

        CTkSegmentedButton needs a few more keywords than the other widgets, so
        it gets its own little styling method instead of a role in theme.py.
        """
        colors = self.theme.colors
        surface = colors["panel"]
        segmented_button.configure(
            fg_color=surface,
            selected_color=colors["text"],
            selected_hover_color=colors["muted"],
            unselected_color=colors["panel"],
            unselected_hover_color=colors["line"],
            text_color=colors["text"],
            bg_color=surface,
            font=self.theme.font("body", bold=True),
            height=self.theme.px(34),
        )

    def _on_theme_applied(self, theme):
        """
        Called by the Theme after every colour change.

        Widgets that were registered with a role are already restyled; this
        method handles the few things that need extra logic.
        """
        # 1. The two segmented buttons.
        self._style_segmented_button(self.contrast_menu)
        self._style_segmented_button(self.size_menu)
        self.contrast_menu.set(self.theme.contrast)
        self.size_menu.set(self.theme.size)

        # 2. The brightness value label and the panel width.
        self.brightness_value_label.configure(text=f"{self.theme.brightness} %")
        self.sidebar.configure(width=self.theme.sidebar_width(),
                               height=WINDOW_SIZE[1] - CONDITION_BAR_HEIGHT)

        # 3. With larger text the window may need more room, otherwise the
        #    status line at the bottom can be pushed out of view.
        self._fit_window()

        # 4. Redraw every task screen (including the one that is hidden).
        for screen in self.tasks.values():
            try:
                screen.on_theme_change()
            except tkinter.TclError:
                pass

    def _fit_window(self):
        """Make the window at least as large as its widgets need."""
        self.update_idletasks()
        needed_width = self.winfo_reqwidth()
        needed_height = self.winfo_reqheight()
        current_width = self.winfo_width()
        current_height = self.winfo_height()
        if needed_width > current_width or needed_height > current_height:
            self.geometry(f"{max(needed_width, current_width)}x"
                          f"{max(needed_height, current_height)}")

    # ------------------------------------------------------------------
    # Events from the control panel
    # ------------------------------------------------------------------

    def on_contrast_change(self, chosen):
        """The experimenter picked High / Medium / Low."""
        self.theme.set_contrast(chosen)
        self.show_status(f"Contrast set to {chosen}.")

    def on_size_change(self, chosen):
        """The experimenter picked Small / Medium / Large."""
        self.theme.set_size(chosen)
        self.show_status(f"Size set to {chosen}.")

    def on_brightness_change(self, value):
        """The brightness slider moved (0-100)."""
        self.theme.set_brightness(value)
        self.brightness_value_label.configure(text=f"{self.theme.brightness} %")

    # ------------------------------------------------------------------
    # Opening the task screens
    # ------------------------------------------------------------------

    def get_participant_id(self):
        """
        Read the Participant ID, asking again if it is empty.

        Returns the ID, or None when the experimenter cancelled.
        """
        participant_id = self.participant_entry.get().strip()
        if participant_id:
            return participant_id

        # No ID yet: explain it and put the cursor in the box (no crash).
        messagebox.showwarning(
            "Participant ID needed",
            "Please type a Participant ID first (for example P01).\n\n"
            "It is written next to every result so you can tell participants "
            "apart later.")
        self.participant_entry.focus_set()
        return None

    def open_identification(self):
        """Show the Identification task (asks for the Participant ID first)."""
        self._open_task("Identification", tasks.IdentificationTask)

    def open_target_hitting(self):
        """Show the Target Hitting task (asks for the Participant ID first)."""
        self._open_task("Target Hitting", tasks.TargetHittingTask)

    def _open_task(self, name, screen_class):
        """Create (once) and show a task screen for the current participant."""
        if not self.leave_current_task():
            return

        participant_id = self.get_participant_id()
        if participant_id is None:
            return

        old_screen = self.tasks.get(name)
        if old_screen is not None:
            old_screen.destroy()          # a new participant = a fresh run
            self.tasks.pop(name, None)

        screen = screen_class(self.content, self.theme, participant_id, self.on_result_saved)
        self.tasks[name] = screen
        self.current_task_name = name
        self._show_screen(
            screen,
            f"{name} task - participant {participant_id}. Follow the instructions "
            f"at the top of the screen. Current condition: {self.theme.condition_text()}.")
        self._update_task_buttons()

    def _show_screen(self, screen, status_message=""):
        """Hide whatever is visible and show `screen` instead."""
        if self.current_screen is not None:
            self.current_screen.grid_forget()
        screen.grid(row=0, column=0, sticky="nsew")
        self.current_screen = screen
        if status_message:
            self.show_status(status_message)

    def show_start_screen(self):
        """Go back to the start screen."""
        if not self.leave_current_task():
            return
        self.current_task_name = None
        self._show_screen(self.start_screen)
        self._update_task_buttons()
        self.show_status(f"Choose a task in the panel on the left. {self._csv_status()}")

    def _update_task_buttons(self):
        """Highlight the task that is open; the other one goes back to normal."""
        for name, button in (("Identification", self.identification_button),
                             ("Target Hitting", self.hitting_button)):
            if name == self.current_task_name:
                button.configure(state="disabled")     # already open
            else:
                button.configure(state="normal")

    def leave_current_task(self):
        """
        Ask before leaving a task that still has unsaved results.

        Returns True when it is fine to continue, False when the user cancelled.
        """
        screen = self.tasks.get(self.current_task_name)
        if screen is None or not hasattr(screen, "has_unsaved_results"):
            return True
        if not screen.has_unsaved_results():
            return True
        return messagebox.askyesno(
            "Unsaved result",
            "This task has a result that has not been saved yet "
            "(it is saved after the 1-5 rating).\n\n"
            "Leave the task and lose it?")

    # ------------------------------------------------------------------
    # Status line
    # ------------------------------------------------------------------

    def show_status(self, message):
        """Show a message in the status line at the bottom of the window."""
        self.status_label.configure(text=message)

    def on_result_saved(self, screen, path):
        """Callback from a task screen after it wrote to results.csv."""
        self.show_status(f"Saved to results.csv ({path}).")
        # "will create" becomes "appending to" after the very first save.
        self._refresh_condition_bar()

    # ------------------------------------------------------------------
    # Closing
    # ------------------------------------------------------------------

    def on_close(self):
        """Make sure unfinished results are not lost silently."""
        if self.leave_current_task():
            self.destroy()


# ============================================================================
# SECTION 3 - Start the application
# ============================================================================

def main():
    """
    Create the window and run the Tk event loop.

    If no graphical display is available (for example on a server, or in an SSH
    session without X forwarding) Tk raises an error.  Printing a short, clear
    message is friendlier than a traceback for a coursework demo.
    """
    try:
        app = App()
    except tkinter.TclError as error:
        print("The window could not be opened:")
        print(f"  {error}")
        print("\nThis usually means there is no graphical display available.")
        print("Run the program from a desktop session, or check that Tkinter")
        print("is installed (for example: sudo apt install python3-tk).")
        return
    app.mainloop()


if __name__ == "__main__":
    main()
