import tkinter as tk


APP_BACKGROUND = "#f7f5ef"
TEXT_COLOR = "#2c241b"
MUTED_TEXT_COLOR = "#7d7468"
STATUS_BACKGROUND = "#ece7de"


# =========================
# Shared GUI Layout Helpers
# =========================
def create_root_window(title, geometry):
    """Create and configure a root Tk window for a listening module."""
    root = tk.Tk()
    root.title(title)
    root.geometry(geometry)
    root.configure(bg=APP_BACKGROUND)
    return root


def create_section_label(parent, text, font=("Arial", 14), padx=30, pady=(10, 4)):
    """Create a left-aligned section label used across modules."""
    label = tk.Label(parent, text=text, font=font, fg=TEXT_COLOR, bg=APP_BACKGROUND)
    label.pack(anchor="w", padx=padx, pady=pady)
    return label


def create_button_row(parent, button_specs, padx=30, pady=(0, 6)):
    """Create a horizontal row of buttons.

    button_specs should be a list of tuples:
    (button_text, command, side_padx)
    """
    row = tk.Frame(parent, bg=APP_BACKGROUND)
    row.pack(anchor="w", padx=padx, pady=pady)

    buttons = []
    for text, command, side_padx in button_specs:
        button = tk.Button(row, text=text, command=command)
        button.pack(side="left", padx=side_padx)
        buttons.append(button)

    return row, buttons


def create_labeled_option_row(
    parent,
    label_text,
    variable,
    options,
    padx=30,
    pady=(0, 6),
    menu_padx=(8, 10),
):
    """Create a labeled dropdown row and return (row, label, option_menu)."""
    row = tk.Frame(parent, bg=APP_BACKGROUND)
    row.pack(anchor="w", padx=padx, pady=pady)

    label = tk.Label(row, text=label_text, fg=TEXT_COLOR, bg=APP_BACKGROUND)
    label.pack(side="left")

    menu = tk.OptionMenu(row, variable, *options)
    menu.pack(side="left", padx=menu_padx)

    return row, label, menu


def create_labeled_option_with_lock_row(
    parent,
    label_text,
    variable,
    options,
    lock_variable,
    lock_text="Lock",
    padx=30,
    pady=(0, 6),
):
    """Create a labeled dropdown row with a lock checkbox.

    Returns (row, label, option_menu, lock_checkbox).
    """
    row, label, menu = create_labeled_option_row(
        parent=parent,
        label_text=label_text,
        variable=variable,
        options=options,
        padx=padx,
        pady=pady,
    )

    lock_checkbox = tk.Checkbutton(row, text=lock_text, variable=lock_variable)
    lock_checkbox.pack(side="left")

    return row, label, menu, lock_checkbox


def create_range_option_row(
    parent,
    label_text,
    start_variable,
    start_options,
    end_variable,
    end_options,
    lock_variable=None,
    lock_text="Lock",
    start_text="Start",
    end_text="End",
    padx=30,
    pady=(0, 6),
):
    """Create a shared range row with start/end dropdowns and optional lock."""
    row = tk.Frame(parent, bg=APP_BACKGROUND)
    row.pack(anchor="w", padx=padx, pady=pady)

    label = tk.Label(row, text=label_text, fg=TEXT_COLOR, bg=APP_BACKGROUND)
    label.pack(side="left")

    start_label = tk.Label(row, text=start_text, fg=TEXT_COLOR, bg=APP_BACKGROUND)
    start_label.pack(side="left", padx=(8, 4))

    start_menu = tk.OptionMenu(row, start_variable, *start_options)
    start_menu.pack(side="left", padx=(0, 10))

    end_label = tk.Label(row, text=end_text, fg=TEXT_COLOR, bg=APP_BACKGROUND)
    end_label.pack(side="left", padx=(0, 4))

    end_menu = tk.OptionMenu(row, end_variable, *end_options)
    end_menu.pack(side="left", padx=(0, 10))

    lock_checkbox = None
    if lock_variable is not None:
        lock_checkbox = tk.Checkbutton(row, text=lock_text, variable=lock_variable)
        lock_checkbox.pack(side="left")

    return row, label, start_label, start_menu, end_label, end_menu, lock_checkbox


def set_option_menu_state(option_menu, state):
    """Set the visual/interactive state of a Tk OptionMenu button."""
    option_menu.configure(state=state)


def set_label_state(label_widget, enabled):
    """Dim or restore a label based on whether its control is active."""
    label_widget.configure(fg=TEXT_COLOR if enabled else MUTED_TEXT_COLOR)


def create_status_panel(parent, wraplength=620, padx=30, pady=(0, 12)):
    """Create a shared status panel style used by listening modules."""
    panel = tk.Label(
        parent,
        text="",
        justify="left",
        anchor="w",
        fg=TEXT_COLOR,
        bg=STATUS_BACKGROUND,
        relief="groove",
        padx=10,
        pady=8,
        wraplength=wraplength,
    )
    panel.pack(anchor="w", fill="x", padx=padx, pady=pady)
    return panel


def bind_live_update(tk_variables, callback):
    """Bind a callback to Tk variable writes for live UI updates."""
    for tk_var in tk_variables:
        tk_var.trace_add("write", lambda *_: callback())
