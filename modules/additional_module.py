import random


# =========================
# Additional Module Helpers
# =========================
def should_randomize(randomization_mode, is_locked):
    """Apply mode + lock policy for non-frequency extension parameters."""
    if randomization_mode == "Use Selected Values":
        return False
    if randomization_mode == "Randomize All":
        return True
    return not is_locked


def resolve_additional_parameters(selected_values, lock_values, option_map, randomization_mode):
    """Resolve optional non-frequency parameters from selected values and locks.

    Args:
        selected_values: Dict of current GUI selections for additional parameters.
        lock_values: Dict of lock-state booleans for additional parameters.
        option_map: Dict mapping parameter name -> list of allowed values.
        randomization_mode: One of Randomize Unlocked / Randomize All / Use Selected Values.

    Returns:
        Dict of resolved parameter values for all keys in option_map.
    """
    resolved = {}
    for name, options in option_map.items():
        if not options:
            continue

        is_locked = lock_values.get(name, False)
        selected = selected_values.get(name, options[0])

        if should_randomize(randomization_mode, is_locked):
            resolved[name] = random.choice(options)
        elif selected in options:
            resolved[name] = selected
        else:
            resolved[name] = options[0]

    return resolved
