"""
tasks.py
========
The two task screens of the Human Perception & Performance Tester.

    IdentificationTask   - vision & perception: "What do you see?" + reaction time
    TargetHittingTask    - Fitts' law: 9 distance x size combinations, 3 trials each

Both screens are built out of CustomTkinter widgets.  Every widget is registered
with the Theme object so that the experimenter's contrast / size / brightness
controls restyle the screen instantly, including the drawings on the Canvas.

Both screens follow the same simple pattern:

    1. the participant types an answer or clicks a target,
    2. the trial is timed with time.perf_counter(),
    3. the participant gives a 1-5 ease-of-use rating,
    4. only then is the row written to results.csv.
"""

import math
import random
import time
import tkinter

from compat import ctk

import logger


# ============================================================================
# SECTION 1 - Settings for the two tasks
# ============================================================================

# ---------------------------------------------------------------------------
# 1a. Identification task
# ---------------------------------------------------------------------------

# The figure is drawn on a 420 x 340 "design grid" and then scaled to the
# Canvas.  Keeping one design grid means the drawing code below never has to
# care about the real window size.
FIGURE_DESIGN_WIDTH = 420
FIGURE_DESIGN_HEIGHT = 340

# Half-width of the Rubin vase measured from the centre line, from top to
# bottom.  A *small* half-width is where the profile of the face sticks out
# (nose, lips, chin); a *large* half-width is where it recedes (eye socket).
# The vase and the two facing profiles are therefore the same outline.
FIGURE_PROFILE = [
    (96, 20),    # rim of the vase / top of the head
    (92, 30),
    (76, 44),
    (64, 56),
    (58, 68),    # forehead
    (66, 82),    # eye socket
    (52, 96),    # nose bridge
    (38, 112),
    (30, 126),   # nose tip
    (42, 136),   # under the nose
    (56, 146),   # upper lip
    (44, 156),   # mouth line
    (54, 166),   # lower lip
    (38, 178),   # chin crease
    (40, 190),   # chin
    (58, 206),   # jaw
    (80, 224),
    (96, 244),   # neck
    (104, 268),
    (114, 296),
    (124, 320),  # foot of the vase
]

# How smooth the outline should be.  Higher = more points = smoother curve.
FIGURE_SMOOTHING_STEPS = 8

# Size of the Canvas the figure is drawn on, in pixels.
ID_CANVAS_WIDTH = 560
ID_CANVAS_HEIGHT = 390

# ---------------------------------------------------------------------------
# 1b. Target hitting task (Fitts' law)
# ---------------------------------------------------------------------------

# How often every distance x size combination is repeated.
# 9 combinations x 3 repetitions = 27 trials per run.
TRIALS_PER_CONDITION = 3

# Distance from the Start button (cursor starting point) in pixels.
# The values are chosen so that even the longest distance plus the largest
# target always fits inside the canvas (see TASK_CANVAS_* and TARGET_ANGLE_RANGES).
TARGET_DISTANCES = {
    "Short": 120,
    "Medium": 200,
    "Long": 280,
}

# Diameter of the target in pixels.
TARGET_SIZES = {
    "Small": 20,
    "Medium": 40,
    "Large": 80,
}

# Size of the Canvas the task is played on.  The canvas is elastic: it grows
# with the window, but the window's minimum size keeps it at least 700 x 340,
# which is enough for the Long distance (280 px) plus the largest target
# radius (40 px) and the edge margin - so a target never has to be moved.
TASK_CANVAS_WIDTH = 760
TASK_CANVAS_HEIGHT = 380

# The Start button (cursor starting point) sits in the middle of the canvas.
START_RATIO_X = 0.50
START_RATIO_Y = 0.55
START_BUTTON_WIDTH = 110
START_BUTTON_HEIGHT = 48

# Random directions (in degrees) the target is placed in: a cone to the right
# (-30 to +30 degrees) or to the left (150 to 210 degrees).  0 degrees points
# right, 90 degrees points down.
TARGET_ANGLE_RANGES = [(-30, 30), (150, 210)]

# Minimum gap (pixels) between the edge of the target and the Canvas border.
CANVAS_EDGE_MARGIN = 16

# Distance of the instruction text from the top of the canvas (pixels).  The
# band above the targets keeps the text readable even with the largest target.
MESSAGE_BAND_Y = 30


# ============================================================================
# SECTION 2 - Small helpers shared by both screens
# ============================================================================

def smooth_polygon(points, steps=FIGURE_SMOOTHING_STEPS):
    """
    Turn a short list of corner points into a smooth, curved outline.

    This is a Catmull-Rom style curve: every segment is bent so that it passes
    through all the given points without sharp corners.  The result is a list
    of (x, y) floats, ready for Canvas.create_polygon().
    """
    padded = [points[0]] + list(points) + [points[-1]]
    curve = []
    for index in range(len(padded) - 3):
        p0, p1, p2, p3 = padded[index:index + 4]
        for step in range(steps):
            t = step / steps
            t2, t3 = t * t, t * t * t
            row = []
            for axis in (0, 1):
                m1 = 0.5 * (p2[axis] - p0[axis])     # incoming tangent
                m2 = 0.5 * (p3[axis] - p1[axis])     # outgoing tangent
                row.append((2 * t3 - 3 * t2 + 1) * p1[axis]
                           + (t3 - 2 * t2 + t) * m1
                           + (-2 * t3 + 3 * t2) * p2[axis]
                           + (t3 - t2) * m2)
            curve.append(tuple(row))
    curve.append(points[-1])
    return curve


def vase_outline(design_width=FIGURE_DESIGN_WIDTH):
    """
    Build the closed Rubin-vase outline on the design grid.

    The right half is the smoothed profile; the left half is its mirror image,
    walked from bottom to top so that the two halves join into one polygon.
    """
    axis = design_width / 2
    curve = smooth_polygon(FIGURE_PROFILE)
    right_half = [(axis + half_width, y) for half_width, y in curve]
    left_half = [(axis - half_width, y) for half_width, y in reversed(curve)]
    return right_half + left_half


class EaseOfUsePanel(ctk.CTkFrame):
    """
    The 1-5 "how easy was that?" prompt shown after every trial.

    The five buttons are numbered and labelled (recognition instead of recall):
        1 Very difficult - 2 Difficult - 3 Neutral - 4 Easy - 5 Very easy

    It is created hidden and shown with ``ask()``.  The chosen number is passed
    back through the callback, so the caller can log the result.
    """

    RATING_LABELS = [
        (1, "1 - Very difficult"),
        (2, "2 - Difficult"),
        (3, "3 - Neutral"),
        (4, "4 - Easy"),
        (5, "5 - Very easy"),
    ]

    def __init__(self, master, theme, on_choice, question="How easy was that trial to use?"):
        super().__init__(master, corner_radius=10, border_width=2)
        self.theme = theme
        self.on_choice = on_choice
        self.rating_buttons = []

        theme.register(self, role="panel")

        self.title_label = ctk.CTkLabel(self, text=question)
        theme.register(self.title_label, role="label", kind="heading", bold=True)

        self.hint_label = ctk.CTkLabel(
            self,
            text="Choose one number to save your result. 1 = very difficult, 5 = very easy.",
        )
        theme.register(self.hint_label, role="hint", kind="small")

        # One row of five numbered buttons.  The row itself is transparent, so
        # the buttons take the colour of the panel behind them.
        self.button_row = ctk.CTkFrame(self, fg_color="transparent")
        theme.register(self.button_row, role="container")
        self.button_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 12))
        for column in range(len(self.RATING_LABELS)):
            self.button_row.grid_columnconfigure(column, weight=1)

        for column, (value, label) in enumerate(self.RATING_LABELS):
            button = ctk.CTkButton(
                self.button_row,
                text=label,
                height=44,
                command=lambda chosen=value: self._choose(chosen),
            )
            # The first three buttons are "hard", the last two "easy".
            theme.register(button, role="primary" if value >= 4 else "secondary",
                           surface="panel", kind="body", bold=True)
            button.grid(row=0, column=column, sticky="ew",
                        padx=(0 if column == 0 else 5, 0))
            self.rating_buttons.append(button)

        self.grid_columnconfigure(0, weight=1)

    def ask(self):
        """Show the prompt and wait for a click (the result is logged later)."""
        self.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))

    def hide(self):
        """Take the prompt off screen again."""
        self.grid_remove()

    def _choose(self, value):
        self.hide()
        self.on_choice(value)


# ============================================================================
# SECTION 3 - Base screen
# ============================================================================

class TaskScreen(ctk.CTkFrame):
    """
    Shared frame for both tasks: an instruction line at the top, the task
    itself in the middle and a status line at the bottom.

    Subclasses fill ``self.body`` and override ``on_theme_change()``.
    """

    TITLE = "Task"
    INSTRUCTIONS = ""
    TASK_TYPE = ""      # value written into the task_type column

    def __init__(self, master, theme, participant_id, on_saved):
        super().__init__(master, fg_color="transparent")
        self.theme = theme
        self.participant_id = participant_id
        self.on_saved = on_saved          # callback(main_window, csv_path)
        self.colors = theme.colors

        theme.register(self, role="container")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # -- row 0: title and instructions --------------------------------
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        theme.register(self.header, role="bg")
        self.header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        self.header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.header, text=self.TITLE, anchor="w")
        theme.register(self.title_label, role="label", surface="bg", kind="title", bold=True)
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.instructions_label = ctk.CTkLabel(
            self.header, text=self.INSTRUCTIONS, anchor="w", justify="left", wraplength=760)
        theme.register(self.instructions_label, role="hint", surface="bg", kind="body")
        self.instructions_label.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.participant_label = ctk.CTkLabel(
            self.header, text="", anchor="e")
        theme.register(self.participant_label, role="label", surface="bg",
                       kind="small", bold=True)
        self.participant_label.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(10, 0))
        self.header.grid_columnconfigure(1, weight=0)

        # -- row 1: the task itself ---------------------------------------
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        theme.register(self.body, role="bg")
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)

        # -- row 2 is reserved for the 1-5 rating prompt of subclasses ------
        # -- row 3: status line --------------------------------------------
        self.status_label = ctk.CTkLabel(self, text="", anchor="w")
        theme.register(self.status_label, role="hint", surface="bg", kind="small")
        self.status_label.grid(row=3, column=0, sticky="ew", padx=16, pady=(2, 10))

    # -- helpers used by both tasks ---------------------------------------

    def show_status(self, message, seconds=8):
        """
        Show a short message on the status line.

        After `seconds` the line switches back to the default text (which
        explains where results are stored).
        """
        self.status_label.configure(text=message)
        self.after(int(seconds * 1000), lambda: self.status_label.configure(text=self.default_status()))

    def default_status(self):
        """Text of the status line when nothing special has happened."""
        return ("Results are appended to results.csv (task: "
                f"{self.TASK_TYPE}, participant: {self.participant_id}).")

    def save_result(self, payload):
        """
        Add the trial data to the CSV file.

        `payload` holds everything except the participant, the visual condition
        and the task name - those are filled in here so that every row is
        complete and consistent.
        """
        row = dict(payload)
        row.update(self.condition)            # snapshot taken when the trial started
        row["participant_id"] = self.participant_id
        row["task_type"] = self.TASK_TYPE

        try:
            path = logger.log_result(row)
        except logger.LogError as error:
            # Friendly message instead of a crash (e.g. file open in Excel).
            self.show_status("Not saved yet - see the message on screen.", 30)
            self._show_error_box("Could not save the result", str(error))
            return False

        self.show_status(f"Saved to results.csv  ({row['task_type']}, "
                         f"participant {self.participant_id})", 10)
        self.on_saved(self, path)
        return True

    def _new_dialog(self, title, size):
        """
        Create a small modal window in the current colours.

        CustomTkinter top-level windows take their colour through configure()
        rather than through a Theme role, so this tiny helper does it once.
        """
        box = ctk.CTkToplevel(self)
        box.title(title)
        box.geometry(size)
        box.configure(fg_color=self.theme.colors["bg"])
        box.grab_set()
        return box

    def _show_error_box(self, title, message):
        """Small modal window for error messages (kept simple on purpose)."""
        box = self._new_dialog(title, "520x260")

        label = ctk.CTkLabel(box, text=message, wraplength=470, justify="left", anchor="w")
        self.theme.register(label, role="label", surface="bg", kind="body")
        label.pack(padx=20, pady=(20, 10), fill="both", expand=True)

        ok_button = ctk.CTkButton(box, text="OK, I closed the file", command=box.destroy)
        self.theme.register(ok_button, role="primary", surface="bg", kind="body", bold=True)
        ok_button.pack(pady=(0, 20))

    def on_theme_change(self, theme=None):
        """Subclasses redraw their Canvas here. Do nothing by default."""
        self.colors = self.theme.colors


# ============================================================================
# SECTION 4 - Task 1: Identification (vision & perception)
# ============================================================================

class IdentificationTask(TaskScreen):
    """
    An ambiguous figure (a Rubin vase: a vase - or two faces looking at
    each other) is drawn on a Canvas.  The participant types what they see.

    Sequence:
        "Show the figure"  ->  figure appears, timer starts
        type an answer + Submit  ->  timer stops, 1-5 rating prompt appears
        choose a rating  ->  the row is written to results.csv
        "Show the figure again"  ->  next trial (e.g. with a new visual condition)
    """

    TITLE = "Task 1 - Identification"
    TASK_TYPE = "Identification"
    INSTRUCTIONS = (
        "1. Look at the figure on the canvas.   2. Type what you see in the box.   "
        "3. Press Submit.   4. Choose how easy it was (1-5).   "
        "5. Use 'Show the figure again' for the next trial - you can change the "
        "visual condition in the panel on the left before each trial."
    )

    IDLE, SHOWING, RATING = "idle", "showing", "rating"

    def __init__(self, master, theme, participant_id, on_saved):
        super().__init__(master, theme, participant_id, on_saved)
        self.state = self.IDLE
        self.start_time = None          # time.perf_counter() when the figure appeared
        self.time_taken = None          # seconds, frozen on Submit
        self.condition = theme.snapshot()
        self.answer = ""
        self.trial_number = 0

        self.participant_label.configure(text=f"Participant: {participant_id}")
        self.status_label.configure(text=self.default_status())

        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        # -- the Canvas with the figure ------------------------------------
        self.canvas_frame = ctk.CTkFrame(self.body, corner_radius=10, border_width=2)
        theme.register(self.canvas_frame, role="panel")
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_rowconfigure(0, weight=1)

        self.canvas = tkinter.Canvas(
            self.canvas_frame, width=ID_CANVAS_WIDTH, height=ID_CANVAS_HEIGHT,
            highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.canvas.bind("<Configure>", lambda event: self.draw_figure())

        # -- answer area ----------------------------------------------------
        self.answer_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        theme.register(self.answer_frame, role="bg")
        self.answer_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.answer_frame.grid_columnconfigure(1, weight=1)

        self.question_label = ctk.CTkLabel(self.answer_frame, text="What do you see?")
        theme.register(self.question_label, role="label", surface="bg",
                       kind="heading", bold=True)
        self.question_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        self.answer_entry = ctk.CTkEntry(
            self.answer_frame, placeholder_text="For example: a vase, two faces, ...")
        theme.register(self.answer_entry, role="entry", surface="bg", kind="body")
        self.answer_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 10))
        # Enter works like pressing Submit, and the box gets the keyboard focus,
        # so the participant can start typing as soon as the trial begins.
        self.answer_entry.bind("<Return>", lambda event: self.submit_answer())

        self.show_button = ctk.CTkButton(self.answer_frame, text="Show the figure",
                                         width=170, height=44, command=self.start_trial)
        theme.register(self.show_button, role="primary", surface="bg", kind="body", bold=True)
        self.show_button.grid(row=1, column=2, sticky="e")

        self.submit_button = ctk.CTkButton(self.answer_frame, text="Submit answer",
                                           width=170, height=44, command=self.submit_answer)
        theme.register(self.submit_button, role="primary", surface="bg", kind="body", bold=True)
        self.submit_button.grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.next_button = ctk.CTkButton(self.answer_frame, text="Show the figure again",
                                         width=200, height=44, command=self.start_trial)
        theme.register(self.next_button, role="secondary", surface="bg", kind="body", bold=True)
        self.next_button.grid(row=2, column=1, sticky="w", pady=(10, 0))

        # -- the 1-5 rating prompt ------------------------------------------
        self.rating_panel = EaseOfUsePanel(
            self, theme, on_choice=self.on_rating_chosen,
            question="How easy was the figure to see and name?")

        self._update_controls()
        self.draw_figure()
        # Put the cursor in the answer box once the screen is on display.
        self.after(100, self.answer_entry.focus_set)

    # -- trial flow --------------------------------------------------------

    def start_trial(self):
        """Show the figure and start the timer for a new trial."""
        self.trial_number += 1
        self.condition = self.theme.snapshot()    # freeze the condition now
        self.answer = ""
        self.time_taken = None

        self.answer_entry.delete(0, "end")
        self.answer_entry.configure(state="normal")
        self.answer_entry.focus_set()

        self.draw_figure(visible=True)            # figure appears ...
        self.state = self.SHOWING
        self.start_time = time.perf_counter()     # ... and the timer starts
        self._update_controls()
        self.show_status(f"Trial {self.trial_number} started - the timer is running. "
                         "Type what you see and press Submit.", 30)

    def submit_answer(self):
        """Stop the timer, check the answer and ask for the 1-5 rating."""
        if self.state != self.SHOWING:
            self.show_status("Press 'Show the figure' first, then type your answer.", 6)
            return

        self.time_taken = time.perf_counter() - self.start_time   # stop the timer

        answer = self.answer_entry.get().strip()
        if not answer:
            # Never crash on empty input: warn, keep the timer running.
            self.show_status("Please type what you see before pressing Submit.", 6)
            self.answer_entry.focus_set()
            self.start_time = time.perf_counter() - self.time_taken  # keep timing
            return

        self.answer = answer
        self.state = self.RATING
        self.answer_entry.configure(state="disabled")
        self._update_controls()
        self.show_status(f"Answer recorded ({self.time_taken:.2f} s). "
                         "Now choose how easy the figure was to see (1-5).", 30)
        self.rating_panel.ask()

    def on_rating_chosen(self, rating):
        """Called by the EaseOfUsePanel once the participant picked 1-5."""
        if self.time_taken is None:
            return          # nothing to save (should not happen)
        payload = {
            "time_taken_seconds": round(self.time_taken, 3),
            "user_response": self.answer,
            "ease_of_use": rating,
            # The remaining columns stay blank for this task.
            "target_distance_px": "",
            "target_size_px": "",
            "error_count": "",
        }
        saved = self.save_result(payload)
        if not saved:
            # Let the participant try the rating again instead of losing data.
            self.rating_panel.ask()
            return

        self.state = self.IDLE
        self._update_controls()
        self.draw_figure()          # figure hidden again until the next trial
        self.show_status(f"Trial {self.trial_number} saved to results.csv. "
                         "Change the visual condition if you like, then press "
                         "'Show the figure again'.", 12)

    def has_unsaved_results(self):
        """True while an answer is waiting for its 1-5 rating."""
        return self.state == self.RATING

    # -- appearance --------------------------------------------------------

    def _update_controls(self):
        """Enable exactly the buttons that make sense in the current state."""
        if self.state == self.IDLE:
            self.show_button.configure(state="normal")
            self.submit_button.configure(state="disabled")
            self.question_label.configure(text="What do you see?  (press 'Show the figure' to start)")
        elif self.state == self.SHOWING:
            self.show_button.configure(state="disabled")
            self.submit_button.configure(state="normal")
            self.question_label.configure(text="What do you see?")
        else:   # RATING
            self.show_button.configure(state="disabled")
            self.submit_button.configure(state="disabled")
            self.question_label.configure(text="Thanks! Now give the 1-5 rating below.")

    def draw_figure(self, visible=None):
        """
        Redraw the ambiguous figure in the current colours and size.

        `visible` defaults to "the figure is visible only while timing", so a
        theme change mid-trial does not hide the figure but a theme change
        while idle does not show it either.
        """
        if visible is None:
            visible = self.state == self.SHOWING

        self.colors = self.theme.colors
        colors = self.colors
        self.canvas.configure(bg=colors["bg"])       # follows brightness/contrast

        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 150)

        if not visible:
            self.canvas.create_text(
                width / 2, height / 2,
                text="Press 'Show the figure' to begin.\nThe timer starts when the figure appears.",
                fill=colors["muted"], font=self.theme.font("body"), justify="center")
            return

        # Scale the design grid so the figure always fits (with a small margin),
        # then apply the Size condition (Small = 60 %, Medium = 80 %, Large = 100 %).
        fit = min(width / FIGURE_DESIGN_WIDTH, height / FIGURE_DESIGN_HEIGHT) * 0.92
        scale = fit * self.theme.figure_scale()
        offset_x = (width - FIGURE_DESIGN_WIDTH * scale) / 2
        offset_y = (height - FIGURE_DESIGN_HEIGHT * scale) / 2

        points = []
        for x, y in vase_outline():
            points.extend((offset_x + x * scale, offset_y + y * scale))

        # A single closed polygon: the vase and the two profiles share it.
        self.canvas.create_polygon(
            points, fill=colors["text"], outline=colors["text"], width=1)

    def on_theme_change(self, theme=None):
        """Called by the Theme after every change of contrast/size/brightness."""
        super().on_theme_change(theme)
        self.draw_figure()
        self.instructions_label.configure(wraplength=max(400, self.winfo_width() - 260))


# ============================================================================
# SECTION 5 - Task 2: Target hitting (Fitts' law)
# ============================================================================

class TargetHittingTask(TaskScreen):
    """
    Fitts' law task.

    Pressing Start ("cursor starting point") makes a circular target appear at
    a random direction and one of three distances away.  The participant clicks
    it as fast as possible.  Every distance x size combination is repeated
    TRIALS_PER_CONDITION times in random order (27 trials by default).

    Clicks that miss the target are counted as errors but do not end the trial.
    The 1-5 rating is asked once at the end of the run and is written to every
    row of that run.
    """

    TITLE = "Task 2 - Target Hitting (Fitts' Law)"
    TASK_TYPE = "Target Hitting"
    INSTRUCTIONS = (
        "1. Press the Start button in the middle of the canvas (that is the cursor "
        "starting point).   "
        "2. A target appears somewhere on the canvas - click it as fast as you can.   "
        "3. Clicks next to the target are counted as errors; keep trying.   "
        "4. After the last trial, give one 1-5 rating. The whole run is then saved."
    )

    RUNNING, RATING, FINISHED = "running", "rating", "finished"

    def __init__(self, master, theme, participant_id, on_saved):
        super().__init__(master, theme, participant_id, on_saved)
        self.state = self.RUNNING
        self.trials = self._build_trial_list()
        self.trial_index = 0
        self.waiting_for_target = False   # target is on screen, timer running
        self.target_center = (0, 0)
        self.target_radius = 0
        self.target_size_name = ""
        self.target_distance_px = 0
        self.error_count = 0
        self.target_time = None           # time.perf_counter() when it appeared

        self.results_buffer = []          # rows waiting for the final rating
        self.start_button_position = (0, 0)

        self.participant_label.configure(text=f"Participant: {participant_id}")
        self.status_label.configure(text=self.default_status())

        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(1, weight=1)

        # -- progress line ---------------------------------------------------
        self.progress_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        theme.register(self.progress_frame, role="bg")
        self.progress_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.progress_frame.grid_columnconfigure(1, weight=1)

        self.trial_label = ctk.CTkLabel(self.progress_frame, text="Trial 0 / 27")
        theme.register(self.trial_label, role="label", surface="bg",
                       kind="heading", bold=True)
        self.trial_label.grid(row=0, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=260)
        theme.register(self.progress_bar, role="progress", surface="bg")
        self.progress_bar.grid(row=0, column=1, sticky="w", padx=16)
        self.progress_bar.set(0)

        self.condition_label = ctk.CTkLabel(self.progress_frame, text="")
        theme.register(self.condition_label, role="hint", surface="bg", kind="small")
        self.condition_label.grid(row=0, column=2, sticky="e")

        # -- the canvas ------------------------------------------------------
        self.canvas_frame = ctk.CTkFrame(self.body, corner_radius=10, border_width=2)
        theme.register(self.canvas_frame, role="panel")
        self.canvas_frame.grid(row=1, column=0, sticky="nsew")
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_rowconfigure(0, weight=1)

        self.canvas = tkinter.Canvas(
            self.canvas_frame, width=TASK_CANVAS_WIDTH, height=TASK_CANVAS_HEIGHT,
            highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        # A new window size means new target positions, so redraw everything.
        self.canvas.bind("<Configure>", self.on_canvas_resized)

        # -- buttons under the canvas ----------------------------------------
        self.button_row = ctk.CTkFrame(self.body, fg_color="transparent")
        theme.register(self.button_row, role="bg")
        self.button_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.button_row.grid_columnconfigure(1, weight=1)

        self.restart_button = ctk.CTkButton(
            self.button_row, text="Restart run", width=160, height=42, command=self.confirm_restart)
        theme.register(self.restart_button, role="secondary", surface="bg", kind="body", bold=True)
        self.restart_button.grid(row=0, column=0, sticky="w")

        self.summary_label = ctk.CTkLabel(self.button_row, text="")
        theme.register(self.summary_label, role="label", surface="bg", kind="body")
        self.summary_label.grid(row=0, column=1, sticky="e")

        # -- the 1-5 rating prompt (used once per run) -------------------------
        self.rating_panel = EaseOfUsePanel(
            self, theme, on_choice=self.on_rating_chosen,
            question="How easy was the whole clicking task?")

        self._update_progress()
        # Draw immediately and once more when the real canvas size is known.
        self.draw_canvas()
        self.canvas.after(50, self.reset_run)

    # -- building the trial list -------------------------------------------

    def _build_trial_list(self):
        """
        All 9 distance x size combinations, repeated TRIALS_PER_CONDITION times
        and shuffled, so the order is randomised for every participant.
        """
        trials = []
        for distance_name in TARGET_DISTANCES:
            for size_name in TARGET_SIZES:
                for _ in range(TRIALS_PER_CONDITION):
                    trials.append((distance_name, size_name))
        random.shuffle(trials)
        return trials

    # -- run control ---------------------------------------------------------

    def reset_run(self):
        """Start a brand new run: new random order, counter back to 1."""
        self.trials = self._build_trial_list()
        self.trial_index = 0
        self.results_buffer = []
        self.state = self.RUNNING
        self.waiting_for_target = False
        self.error_count = 0
        self.summary_label.configure(text="")
        self.draw_canvas()
        self._update_progress()

    def confirm_restart(self):
        """Ask before throwing away a half-finished run."""
        if not self.results_buffer and self.state == self.RUNNING and self.trial_index == 0:
            self.reset_run()
            return
        box = self._new_dialog("Restart this run?", "440x210")

        label = ctk.CTkLabel(box, text=("Restart the run? Trials that have not been saved yet "
                                        "will be lost."), wraplength=370, justify="left")
        self.theme.register(label, role="label", surface="bg", kind="body")
        label.pack(padx=20, pady=20)

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(pady=(0, 20))
        yes = ctk.CTkButton(row, text="Yes, restart", width=140,
                            command=lambda: (box.destroy(), self.reset_run()))
        no = ctk.CTkButton(row, text="No, keep going", width=140, command=box.destroy)
        self.theme.register(yes, role="primary", surface="bg", kind="body", bold=True)
        self.theme.register(no, role="secondary", surface="bg", kind="body", bold=True)
        yes.pack(side="left", padx=8)
        no.pack(side="left", padx=8)

    # -- one trial -----------------------------------------------------------

    def on_canvas_resized(self, event):
        """The window was resized: redraw at the new size (target included)."""
        if self.state == self.FINISHED:
            return              # nothing on the canvas that could be resized
        self.draw_canvas(target_visible=self.waiting_for_target)

    def start_trial(self):
        """Called by the Start button: place a target and start timing."""
        if self.state != self.RUNNING or self.waiting_for_target:
            return
        if self.trial_index >= len(self.trials):
            self.finish_run()
            return

        # Freeze the visual condition at the moment this trial starts.
        self.conditions_snapshot = self.theme.snapshot()
        distance_name, size_name = self.trials[self.trial_index]
        self.target_size_name = size_name
        self.target_distance_px = TARGET_DISTANCES[distance_name]
        self.target_radius = TARGET_SIZES[size_name] / 2
        self.error_count = 0

        self.target_center = self._random_target_position(self.target_distance_px,
                                                          self.target_radius)
        self.draw_canvas(target_visible=True)
        self.waiting_for_target = True
        self.target_time = time.perf_counter()      # the timer starts NOW

    def _random_target_position(self, distance, radius):
        """
        Pick a random direction and return the centre of the target.

        The direction is random, but a position is only accepted when the whole
        target fits inside the canvas.  Up to 200 directions are tried; if the
        window is ever made so small that nothing fits, the target is moved
        closer to the start point as a last resort so the task never breaks.
        """
        width = max(self.canvas.winfo_width(), 300)
        height = max(self.canvas.winfo_height(), 200)
        start_x, start_y = self.start_button_position

        # The gap the target needs between its edge and the canvas border.
        gap = radius + CANVAS_EDGE_MARGIN
        current_distance = distance

        for shrink_step in range(6):
            for attempt in range(200):
                lowest, highest = random.choice(TARGET_ANGLE_RANGES)
                angle = math.radians(random.uniform(lowest, highest))
                x = start_x + math.cos(angle) * current_distance
                y = start_y + math.sin(angle) * current_distance
                if gap <= x <= width - gap and gap <= y <= height - gap:
                    return (x, y)
            # No direction fitted: the window is too small for this distance.
            current_distance -= 20

        # Final fallback: place the target straight to the side of the start.
        side = 1 if start_x < width / 2 else -1
        return (start_x + side * current_distance, start_y)

    def on_canvas_click(self, event):
        """
        A click on the canvas.

        * a click inside the target stops the timer and stores the trial,
        * a click outside the target counts as an error and the trial continues.
        """
        if not self.waiting_for_target:
            return

        offset_x = event.x - self.target_center[0]
        offset_y = event.y - self.target_center[1]
        inside = math.hypot(offset_x, offset_y) <= self.target_radius

        if not inside:
            self.error_count += 1
            self.draw_canvas(target_visible=True)   # keep the target on screen
            self.show_status(f"Missed! Errors this trial: {self.error_count}. "
                             "Keep clicking the target.", 4)
            return

        # Hit: stop the timer for this trial.
        elapsed = time.perf_counter() - self.target_time
        self.waiting_for_target = False

        # The distance is measured from the Start point to the centre of the
        # target on screen (it equals the planned distance unless the target had
        # to be moved because the window was small).
        start_x, start_y = self.start_button_position
        measured_distance = math.hypot(self.target_center[0] - start_x,
                                       self.target_center[1] - start_y)
        if abs(measured_distance - self.target_distance_px) > 1:
            measured_distance = round(measured_distance)

        self.results_buffer.append({
            "time_taken_seconds": round(elapsed, 3),
            "target_distance_px": measured_distance,
            "target_size_px": TARGET_SIZES[self.target_size_name],
            "error_count": self.error_count,
            "user_response": "",
            "condition": self.conditions_snapshot,
        })

        self.trial_index += 1
        self._update_progress()

        if self.trial_index >= len(self.trials):
            self.finish_run()
        else:
            self.draw_canvas()      # hide the target, show "click Start" message
            self.show_status(f"Trial {self.trial_index} of {len(self.trials)} recorded "
                             f"({elapsed:.2f} s, {self.error_count} error(s)). "
                             "Press Start for the next trial.", 10)

    def finish_run(self):
        """All trials are done: ask for the single 1-5 rating of this run."""
        self.state = self.RATING
        self.waiting_for_target = False
        self.draw_canvas()
        self._update_progress()
        self.summary_label.configure(
            text=f"Run finished: {len(self.results_buffer)} trials. Thank you!")
        self.show_status("Run finished. Please give ONE 1-5 rating for the whole run; "
                         "all trials are saved after that.", 60)
        self.rating_panel.ask()

    def has_unsaved_results(self):
        """True while a run has trials that have not been written to the CSV."""
        return bool(self.results_buffer)

    def on_rating_chosen(self, rating):
        """
        Save the whole run: one row per trial, all with the same rating.

        If saving fails (file open in Excel) the rating prompt comes back so
        nothing is lost.
        """
        saved_rows = 0
        for trial in self.results_buffer:
            payload = {
                "time_taken_seconds": trial["time_taken_seconds"],
                "target_distance_px": trial["target_distance_px"],
                "target_size_px": trial["target_size_px"],
                "error_count": trial["error_count"],
                "user_response": "",
                "ease_of_use": rating,
            }
            row = dict(payload)
            row.update(trial["condition"])       # condition at the time of the trial
            row["participant_id"] = self.participant_id
            row["task_type"] = self.TASK_TYPE
            try:
                logger.log_result(row)
            except logger.LogError as error:
                self.show_status(f"Saved {saved_rows} of {len(self.results_buffer)} trials. "
                                 "The rest could not be written.", 30)
                self._show_error_box("Could not save the results", str(error))
                self.rating_panel.ask()          # let the user try again
                return
            saved_rows += 1

        self.state = self.FINISHED
        self.results_buffer = []
        self.summary_label.configure(
            text=f"Saved {saved_rows} trials with ease-of-use rating {rating}.")
        self.show_status(f"Saved to results.csv ({saved_rows} rows, rating {rating}). "
                         "Press 'Restart run' to test another participant.", 20)
        self.on_saved(self, logger.CSV_PATH)
        self._update_progress()

    # -- drawing -------------------------------------------------------------

    def draw_canvas(self, target_visible=False):
        """
        Redraw the whole Fitts canvas.

        Called when a trial starts or ends, when the window is resized and after
        every theme change - so contrast/brightness always apply to the target.
        """
        self.colors = self.theme.colors
        colors = self.colors
        self.canvas.configure(bg=colors["bg"])
        self.canvas.delete("all")

        width = max(self.canvas.winfo_width(), 300)
        height = max(self.canvas.winfo_height(), 200)

        # Remember where the Start button is (it is the cursor starting point).
        self.start_button_position = (width * START_RATIO_X, height * START_RATIO_Y)

        # Faint outline so the clickable area is obvious.
        self.canvas.create_rectangle(
            2, 2, width - 2, height - 2, outline=colors["line"], width=2)

        # -- an instruction or message above the Start button ----------------
        if target_visible:
            message = ("Click the target as fast as you can. Clicks next to it "
                       f"count as errors (errors so far: {self.error_count}).")
        elif self.state == self.RATING:
            message = "Run finished - give the 1-5 rating below."
        elif self.state == self.FINISHED:
            message = "This run is saved. Press 'Restart run' for a new participant."
        else:
            message = "Press Start to begin the next trial."

        # The message sits in the top band of the canvas.  Targets only ever
        # appear left or right of the middle (see TARGET_ANGLE_RANGES), so the
        # text and the task never overlap.
        self.canvas.create_text(
            width / 2, MESSAGE_BAND_Y, text=message, fill=colors["text"],
            font=self.theme.font("heading", bold=True), width=width * 0.85)

        # -- the Start button (the cursor starting point) --------------------
        # It is always drawn at the same fixed position, so the participant can
        # see the distance to the target. While a trial is running it is greyed
        # out, because clicking it does nothing until the target is hit.
        start_x, start_y = self.start_button_position
        button_w = self.theme.px(START_BUTTON_WIDTH)
        button_h = self.theme.px(START_BUTTON_HEIGHT)
        button_box = (start_x - button_w / 2, start_y - button_h / 2,
                      start_x + button_w / 2, start_y + button_h / 2)

        start_enabled = self.state == self.RUNNING and not target_visible
        button_id = self.canvas.create_rectangle(
            *button_box,
            fill=colors["accent"] if start_enabled else colors["line"],
            outline=colors["text"], width=2)
        text_id = self.canvas.create_text(
            start_x, start_y, text="START",
            fill=colors["on_accent"] if start_enabled else colors["muted"],
            font=self.theme.font("heading", bold=True))

        if start_enabled:
            # Clicking either the rectangle or its text starts a trial.
            self.canvas.tag_bind(button_id, "<Button-1>", lambda event: self.start_trial())
            self.canvas.tag_bind(text_id, "<Button-1>", lambda event: self.start_trial())
            self.canvas.configure(cursor="hand2")
        else:
            self.canvas.configure(cursor="")

        # -- the target (drawn last so it is on top) -------------------------
        if target_visible:
            # The circle is drawn with exactly the radius used for hit testing,
            # so what the participant sees is what they can click.
            radius = self.target_radius
            x, y = self.target_center
            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=colors["accent"], outline=colors["on_accent"], width=2)
            # A label only fits inside the larger targets.
            if radius >= 24:
                self.canvas.create_text(
                    x, y, text="CLICK", fill=colors["on_accent"],
                    font=self.theme.font("small", bold=True))

    def _update_progress(self):
        """Refresh the 'Trial x / 27' label, the progress bar and the condition."""
        total = len(self.trials)
        done = min(self.trial_index, total)
        if self.state == self.RUNNING and not self.waiting_for_target:
            # The trial that is about to start is the current one.
            text = f"Trial {min(done + 1, total)} / {total}"
        elif self.state == self.RUNNING:
            # A trial is being timed right now: it is not finished yet.
            text = f"Trial {done + 1} / {total}  (in progress)"
        else:
            text = f"Trials done: {done} / {total}"
        self.trial_label.configure(text=text)
        self.progress_bar.set(0 if total == 0 else done / total)
        condition = self.theme.snapshot()
        self.condition_label.configure(
            text=f"Condition during this run: {condition['visual_condition']}")

    def on_theme_change(self, theme=None):
        """Restyle the drawing and the labels after a visual change."""
        super().on_theme_change(theme)
        self.draw_canvas(target_visible=self.waiting_for_target)
        self._update_progress()
        self.instructions_label.configure(wraplength=max(400, self.winfo_width() - 260))
