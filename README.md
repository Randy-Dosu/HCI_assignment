# Human Perception & Performance Tester

A small Python desktop application for an HCI (Human-Computer Interaction)
coursework.  It runs two classic perception / performance experiments and
records every trial in a CSV file, while the experimenter can change three
visual variables at any time:

* **Contrast** - High, Medium or Low
* **Size** - Small, Medium or Large
* **Brightness** - a 0-100 % slider that simulates a dimmer screen

Everything on screen (text, buttons and the drawings on the task canvases)
follows these three settings immediately.

---

## 1. Installation

You need **Python 3.10 or newer** (the code is plain Python 3 with no
version-specific tricks).  Tkinter is part of the standard Python installer on
Windows and macOS.  On Linux install it with your package manager, for example:

```bash
sudo apt install python3-tk
```

Then install the only dependency:

```bash
pip install customtkinter
```

> If CustomTkinter is **not** installed the program still starts: `compat.py`
> automatically falls back to standard Tkinter widgets, so the app keeps working
> (with simpler styling).

## 2. Running the app

From the folder that contains `main.py`:

```bash
python main.py
```

On some systems the command is `python3 main.py`.

`results.csv` is created automatically the first time a result is saved.

After a session you can print a short summary of the data (optional):

```bash
python analyse.py
```

---

## 3. How to run a session (step by step)

1. Type a **Participant ID** (for example `P01`) in the panel on the left.
2. Choose the visual condition: **Contrast**, **Size**, **Brightness**.
   The line at the top always shows the active condition, e.g.
   `Active condition: Contrast: Low | Size: Small | Brightness: 60%`.
3. Click **Identification** or **Target Hitting**.
4. Follow the instructions printed at the top of the task screen - every step
   has its own labelled button.
5. Results are written to `results.csv`; the status line at the bottom says
   *"Saved to results.csv"* after each save.

You can change the three visual controls **at any time**, also in the middle of
a session.  Each trial is logged with the condition that was active when the
trial *started*.

---

## 4. Features

### 4.1 Experimenter control panel (always visible)

| Control | What it does |
|---|---|
| **Contrast: High / Medium / Low** | Switches the colour palette of the whole interface and of the task canvases. Ratios (WCAG, text vs. background): High **21.0 : 1**, Medium **5.1 : 1**, Low **1.7 : 1**. |
| **Size: Small / Medium / Large** | Changes every font size (about 11 / 14 / 18 pt body text) and every shape size (radio buttons, slider, progress bar, Start button, and the ambiguous figure). Only sizes change - never positions. |
| **Brightness 0-100 %** | Scales all colours towards black, on top of the selected contrast mode. It updates live while the slider is dragged. |

The slider knob always stays visible (even at 0 %), so the experimenter can
never "lose" the window in the dark.

### 4.2 Identification task (vision & perception)

* An **ambiguous figure** is drawn with Canvas shapes: a *Rubin vase*, i.e. a
  vase that is also two human faces looking at each other.  No image files are
  used - it is one closed polygon generated from a short list of profile points.
* The figure's colour follows contrast + brightness; its size follows the
  **Size** setting.
* **Show the figure** starts the trial and the timer (`time.perf_counter()`).
* The participant types an answer ("What do you see?") and presses
  **Submit answer** (the Enter key works too).  The timer stops on Submit.
* An empty answer is not accepted: a warning is shown and the timer keeps
  running - the app never crashes on empty input.
* After every submission the participant gives a **1-5 ease-of-use rating**
  using five clearly labelled buttons (1 = very difficult ... 5 = very easy).
  The row is written to the CSV **only after** the rating is chosen.
* **Show the figure again** starts the next trial, so the experimenter can
  change the visual condition in between.

### 4.3 Target hitting task (Fitts' law)

* A **Start** button is drawn at a fixed position in the middle of the canvas;
  it is the **cursor starting point**.
* Clicking Start immediately draws a **circular target** at a random angle
  (a left or right cone) at one of three distances:
  **Short 120 px, Medium 200 px, Long 280 px** (the canvas is 760 x 380 and
  grows with the window, and the minimum window size still leaves about
  700 x 340 px, so every target always fits at its full distance).
* Target sizes: **Small 20 px, Medium 40 px, Large 80 px** (diameter).
* All **9 distance x size combinations** are run **3 times each = 27 trials**
  (the repetition count is the constant `TRIALS_PER_CONDITION` at the top of
  `tasks.py`), in a **randomised** order that is reshuffled for every run.
* A progress indicator shows **"Trial 5 / 27"** plus a progress bar.
* The time from the target appearing to the target being clicked is measured
  with `time.perf_counter()`.
* Clicks that miss the target are counted as **errors** (`error_count`) and the
  trial continues - the participant keeps clicking until they hit it.
* After the **whole run** the participant gives **one** 1-5 rating; that rating
  is written to every row of the run.  Asking once per run keeps the flow
  uninterrupted.
* The target placement is always validated against the canvas bounds, and the
  logged distance is the measured distance from Start to the target centre
  (it equals the planned distance whenever the target fits normally).

---

## 5. results.csv

The file is created with a header the first time something is saved and is
**never overwritten** - later runs append new rows, so a whole class can share
one file.

| Column | Meaning |
|---|---|
| `participant_id` | the ID typed in the control panel |
| `timestamp` | local date and time, `YYYY-MM-DD HH:MM:SS` |
| `visual_condition` | e.g. `Contrast=Low; Size=Small; Brightness=60` |
| `contrast` | `High` / `Medium` / `Low` |
| `size` | `Small` / `Medium` / `Large` |
| `brightness` | `0` - `100` |
| `task_type` | `Identification` or `Target Hitting` |
| `time_taken_seconds` | measured time, rounded to 3 decimals |
| `target_distance_px` | blank for Identification |
| `target_size_px` | blank for Identification |
| `error_count` | blank for Identification |
| `user_response` | the typed answer (blank for Target Hitting) |
| `ease_of_use` | `1` - `5` |

If the file is open in Excel (or another program) while a result is saved, the
app shows a friendly message and the rating prompt / run stays on screen so no
data is lost - just close the file and try again.

---

## 6. Project structure

```
HCI_assignment/
├── main.py            # entry point + main window, control panel, task menu
├── tasks.py           # the two task screens (Identification, Target Hitting)
├── theme.py           # contrast palettes, size tables, brightness maths
├── logger.py          # CSV logging helper (header, append, error handling)
├── compat.py          # one import for CustomTkinter, with a Tkinter fallback
├── analyse.py         # optional: prints summary tables from results.csv
├── requirements.txt   # the single dependency
├── results.csv        # created automatically; not tracked by git
└── README.md
```

All configurable values live in clearly named constants at the top of the files:

* `theme.py` - contrast palettes, font sizes, size multipliers, sidebar widths
* `tasks.py` - `TRIALS_PER_CONDITION`, `TARGET_DISTANCES`, `TARGET_SIZES`,
  canvas size, angle ranges, the figure's profile points
* `logger.py` - the CSV path and the column order

---

## 7. Design choices (usability)

* **Recognition over recall** - every screen prints numbered instructions and
  every step has its own labelled button.  Buttons that make no sense in the
  current state are disabled rather than hidden, so the layout never jumps.
* **Immediate feedback** - the active condition is always visible at the top,
  the status line reports every save, and the progress bar shows how much of the
  Fitts run is left.
* **Forgiving input** - empty Participant ID or empty answer shows a warning
  instead of an error; a half-finished Fitts run asks before it is thrown away;
  a locked `results.csv` can be retried without losing the trial.
* **Accessible variable** - the Low contrast mode is still legible (about
  1.7 : 1) but clearly hard to read, which is exactly what the experiment needs.

---

## 8. Notes for the report

* WCAG contrast ratios were computed with `theme.contrast_ratio()`, the same
  function that is in the source code.
* The figure is a single closed polygon whose left half mirrors its right half;
  the vase outline and the two facing profiles are therefore physically the same
  edge - the classic Rubin vase demonstration of figure-ground organisation.
* Fitts' law predicts that movement time grows with the *index of difficulty*
  `ID = log2(2D / W)`; the logged `target_distance_px` and `target_size_px`
  columns are everything needed to compute it.

---

## 9. Where each requirement is implemented

| Requirement | Where |
|---|---|
| Entry point and main window | `main.py` → `main()` / `class App` |
| Contrast: High / Medium / Low (radio-style control) | `main.py` → `_build_sidebar()` (`CTkSegmentedButton`), palettes in `theme.py` → `CONTRAST_PALETTES` |
| Contrast applies to text, buttons and the task canvases | `theme.py` → `Theme._style_one()` for widgets, `tasks.py` → `draw_figure()` / `draw_canvas()` for the Canvas |
| Size: Small / Medium / Large (fonts + shape sizes only) | `theme.py` → `FONT_SCALE`, `SHAPE_SCALE`, `FIGURE_SCALE`, `SIDEBAR_WIDTH`; applied by `Theme.font()` / `Theme.px()` / `Theme.figure_scale()` |
| Brightness slider 0-100 %, live, on top of contrast | `main.py` → `on_brightness_change()` → `Theme.set_brightness()`; maths in `theme.py` → `scale_color()`, `build_colors()` |
| Active condition shown at the top | `main.py` → `_build_condition_bar()` / `_refresh_condition_bar()`, text from `Theme.condition_text()` |
| All three controls restyle the whole interface immediately | `theme.py` → `Theme.apply()` walks every registered widget, then calls the listeners that redraw the Canvases |
| Menu/tabs to choose a task + Participant ID field | `main.py` → `_build_sidebar()` (two task buttons, ID entry), `get_participant_id()` |
| Identification: ambiguous figure drawn with Canvas shapes | `tasks.py` → `FIGURE_PROFILE`, `smooth_polygon()`, `vase_outline()`, `IdentificationTask.draw_figure()` |
| Figure colour follows contrast/size/brightness | `IdentificationTask.draw_figure()` uses `self.theme.colors` and `theme.figure_scale()` |
| Text entry + Submit ("What do you see?") | `IdentificationTask.__init__()` (`answer_entry`, `submit_button`), `submit_answer()` |
| Timer with `time.perf_counter()` | `IdentificationTask.start_trial()` / `submit_answer()` |
| Repeatable: "Show the figure again" | `IdentificationTask.next_button` → `start_trial()` |
| 1-5 ease-of-use prompt, 5 labelled buttons, logged only after the rating | `EaseOfUsePanel`, `IdentificationTask.on_rating_chosen()` |
| Fitts: Start button at a fixed position | `tasks.py` → `START_RATIO_X/Y` and `draw_canvas()` (the START rectangle) |
| Fitts: target appears immediately after Start | `TargetHittingTask.start_trial()` |
| Fitts: distances Short/Medium/Long, sizes Small/Medium/Large | `TARGET_DISTANCES`, `TARGET_SIZES` |
| Fitts: 9 combinations x 3 repetitions, randomised | `TRIALS_PER_CONDITION`, `_build_trial_list()` |
| Fitts: progress indicator "Trial 5 / 27" | `_update_progress()` (label + `CTkProgressBar`) |
| Fitts: random direction but always inside the canvas | `TARGET_ANGLE_RANGES`, `_random_target_position()` |
| Fitts: `time.perf_counter()` timing | `TargetHittingTask.start_trial()` / `on_canvas_click()` |
| Fitts: misses counted as `error_count`, trial continues | `on_canvas_click()` (the `not inside` branch) |
| Fitts: one 1-5 rating at the end, written to all rows | `finish_run()`, `on_rating_chosen()` |
| CSV created with the exact header, appended, never overwritten | `logger.py` → `COLUMNS`, `_ensure_header()`, `log_result()` |
| `time_taken_seconds` rounded to 3 decimals | `logger.py` → `_format_value()`, plus `round(..., 3)` in `tasks.py` |
| Status line "Saved to results.csv" | `TaskScreen.show_status()` / `save_result()`, `App.show_status()` |
| CSV locked (PermissionError) handled with a friendly message | `logger.py` → `LogError`; `tasks.py` → `save_result()`, `_show_error_box()`; the rating prompt comes back so nothing is lost |
| No crash on empty Participant ID / empty answer | `App.get_participant_id()`, `IdentificationTask.submit_answer()` |
| Docstrings, comments, constants at the top of each file | every module has numbered `SECTION` blocks and named constants |
| Falls back to standard Tkinter | `compat.py` → `USING_CUSTOMTKINTER`, `_build_fallback_module()` |
| Python 3.10+ on Windows / macOS / Linux | standard library + `customtkinter` only; no OS-specific paths (see `logger.CSV_PATH`) |

### A note on the fallback mode

Launching with CustomTkinter installed is the intended way to run the app.
`compat.py` exists so the program still opens (with plain Tk styling) if a
computer in the lab does not have CustomTkinter.  It translates the handful of
CustomTkinter keyword arguments the app uses into plain Tk options and ignores
the purely cosmetic ones (`corner_radius`, `fg_color`, ...).
