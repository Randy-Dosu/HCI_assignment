"""
logger.py
=========
CSV logging for the Human Perception & Performance Tester.

Every finished trial is appended to ``results.csv``.  The file is created (with
a header row) the first time a result is saved and is never overwritten: later
runs simply append new rows, so a whole class can use one file.

If the file cannot be written - the usual reason is that somebody opened it in
Excel - a friendly :class:`LogError` is raised instead of crashing the app.
"""

import csv
import os
from datetime import datetime


# ============================================================================
# SECTION 1 - Settings
# ============================================================================

# results.csv is stored next to this file, no matter where the app is started.
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.csv")

# The column order is fixed by the assignment.  Changing the names here changes
# the header of newly created files only - never edit a file that already
# exists, because older rows would no longer line up with the new header.
COLUMNS = [
    "participant_id",
    "timestamp",
    "visual_condition",
    "contrast",
    "size",
    "brightness",
    "task_type",
    "time_taken_seconds",
    "target_distance_px",
    "target_size_px",
    "error_count",
    "user_response",
    "ease_of_use",
]


# ============================================================================
# SECTION 2 - Error type and helper functions
# ============================================================================

class LogError(Exception):
    """Raised when a result could not be saved. The message is user friendly."""


def timestamp_now():
    """
    Current local date and time as 'YYYY-MM-DD HH:MM:SS'.

    The format sorts correctly as text and opens nicely in Excel / LibreOffice.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def csv_exists():
    """True if results.csv is already there (used for the status line)."""
    return os.path.exists(CSV_PATH)


def _format_value(value):
    """Convert a value to the text that is written into the CSV file."""
    if value is None:
        return ""
    if isinstance(value, float):
        # Milliseconds matter for the Fitts task, so keep 3 decimals.
        return f"{value:.3f}"
    return str(value)


def _build_row(result):
    """
    Turn a result dictionary into a list that matches COLUMNS exactly.

    Missing keys become empty cells, which is exactly what the assignment asks
    for: the target columns stay blank for Identification rows, and
    user_response stays blank for Target Hitting rows.
    """
    return [_format_value(result.get(column, "")) for column in COLUMNS]


def _ensure_header():
    """
    Create results.csv with a header row if it does not exist yet.

    ``newline=""`` is required by the csv module on Windows, otherwise blank
    lines appear between the rows.
    """
    if os.path.exists(CSV_PATH):
        return
    try:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(COLUMNS)
    except PermissionError as error:
        raise LogError(
            "results.csv could not be created.\n\n"
            "Please close the file if it is open in Excel or another program, "
            "then try again."
        ) from error


# ============================================================================
# SECTION 3 - The public logging function
# ============================================================================

def log_result(result):
    """
    Append one result dictionary to results.csv.

    Parameters
    ----------
    result : dict
        Keys are the column names from COLUMNS.  Missing keys are written as
        blank cells.  A 'timestamp' is added automatically when not supplied.

    Returns
    -------
    str
        The path of the CSV file that was written to.

    Raises
    ------
    LogError
        If the file is locked (for example open in Excel) or the folder is not
        writable.  The message can be shown to the user as it is.
    """
    _ensure_header()

    row = dict(result)
    row.setdefault("timestamp", timestamp_now())

    try:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(_build_row(row))
    except PermissionError as error:
        raise LogError(
            "Could not save the result because results.csv is open in "
            "another program (for example Excel).\n\n"
            "Close the file and press the button again - your result has NOT "
            "been lost unless you leave this screen."
        ) from error
    except OSError as error:
        raise LogError(
            f"Could not write to {CSV_PATH}.\n\n"
            f"The system reported: {error.strerror or error}\n\n"
            "Check that the folder is writable and try again."
        ) from error

    return CSV_PATH


def read_results():
    """
    Read results.csv back as a list of dictionaries (used by the analysis
    script).  Returns an empty list when the file does not exist yet.
    """
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))
