import csv
import atexit
import os
import shutil
import tkinter as tk
import subprocess
import tempfile
import threading
from datetime import datetime
from tkinter import filedialog
from tkinter import ttk

import numpy as np
import soundfile as sf

from app.common_gui import bind_live_update
from app.common_gui import create_button_row
from app.common_gui import create_labeled_option_row
from app.common_gui import create_labeled_option_with_lock_row
from app.common_gui import create_range_option_row
from app.common_gui import create_root_window
from app.common_gui import create_section_label
from app.common_gui import create_status_panel
from app.common_gui import MUTED_TEXT_COLOR
from app.common_gui import TEXT_COLOR
from app.common_gui import set_label_state
from app.common_gui import set_option_menu_state

from audio_processing import (
    BAND_MODES,
    AUTOMOBILE_AC_OPTIONS,
    AUTOMOBILE_CABIN_OPTIONS,
    AUTOMOBILE_LOUDNESS_OPTIONS,
    BOOST_GAIN_OPTIONS,
    CUT_GAIN_OPTIONS,
    FILTER_COUNT_OPTIONS,
    GAIN_DIRECTION_OPTIONS,
    GAIN_OPTIONS,
    Q_OPTIONS,
    RANDOMIZATION_MODES,
    create_automobile_conditioned_audio,
    create_modified_audio,
    create_trial_audio,
    get_frequency_options,
    resolve_no_change_probability,
    resolve_trial_parameters,
)

RUNTIME_AUDIO_DIR = tempfile.mkdtemp(prefix="critical_listening_")
modified_file = os.path.join(RUNTIME_AUDIO_DIR, "modified.wav")
match_file = os.path.join(RUNTIME_AUDIO_DIR, "match_guess.wav")
memorization_file = os.path.join(RUNTIME_AUDIO_DIR, "memorization.wav")
selected_section_file = os.path.join(RUNTIME_AUDIO_DIR, "selected_section.wav")
trial_reference_file = os.path.join(RUNTIME_AUDIO_DIR, "trial_reference.wav")
trial_modified_file = os.path.join(RUNTIME_AUDIO_DIR, "trial_modified.wav")
reference_file = ""
SESSION_EXPORT_DIR = "results"

TEST_MODE_OPTIONS = [
    "Mode 1: Detect Change",
    "Mode 2: Identify Setting",
]
IDENTIFICATION_TARGET_OPTIONS = ["Frequency", "Q", "Gain"]
NO_CHANGE_RATE_OPTIONS = ["Random", "0%", "25%", "50%", "75%"]
MAX_FILTERS_PER_TRIAL = 3
SECTION_LENGTH_OPTIONS = [3, 5, 8, 10, 15, 20, 30]
AUTOMOBILE_MONITOR_OPTIONS = ["Off", "On"]
AUTOMOBILE_PRESET_OPTIONS = [
    "Neutral Cabin",
    "City Commute",
    "Highway With AC",
    "Windows Open Loud",
]
AUTOMOBILE_PRESET_SETTINGS = {
    "Neutral Cabin": {
        "monitoring": "On",
        "cabin": "Parked Cabin",
        "ac": "Off",
        "loudness": "Reference",
    },
    "City Commute": {
        "monitoring": "On",
        "cabin": "City Streets",
        "ac": "Low",
        "loudness": "Comfort",
    },
    "Highway With AC": {
        "monitoring": "On",
        "cabin": "Highway Cruise",
        "ac": "Medium",
        "loudness": "Commute",
    },
    "Windows Open Loud": {
        "monitoring": "On",
        "cabin": "Windows Open",
        "ac": "Off",
        "loudness": "Loud",
    },
}

audio_process = None
modified_sample = None

current_frequency = None
current_gain = None
current_q = None
current_band_mode = None
current_filters = []
current_trial_has_change = None
current_trial_id = 0
current_trial_scored = False
last_feedback = "No answer checked yet"
session_results = []
session_events = []
waveform_mono_data = None
waveform_sample_rate = None
waveform_duration_seconds = 0.0
selected_section_start_seconds = None
selected_section_end_seconds = None
pending_detection_answer = None
auto_select_thread = None
auto_select_running = False
auto_select_spinner_after_id = None
auto_select_spinner_index = 0
auto_select_spinner_frames = ["|", "/", "-", "\\"]
auto_select_done_flash_after_id = None


def cleanup_runtime_audio_dir():
    """Delete temporary runtime audio artifacts for this app session."""
    if os.path.isdir(RUNTIME_AUDIO_DIR):
        shutil.rmtree(RUNTIME_AUDIO_DIR, ignore_errors=True)


atexit.register(cleanup_runtime_audio_dir)


# =========================
# Status Display Helpers
# =========================
def format_value_for_status(value):
    """Format values for clean status text (e.g., show 1.0 as 1)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def format_no_change_rate_for_status():
    """Format the mode-1 no-change rate for the live status panel."""
    value = selected_no_change_rate.get()
    if value in {None, "", "Random"}:
        return "Random"
    if isinstance(value, str):
        return value
    return f"{value}%"


def build_automobile_environment_settings():
    """Collect active automobile simulation options from Tk variables."""
    return {
        "enabled": selected_automobile_monitoring.get() == "On",
        "cabin_profile": selected_automobile_cabin.get(),
        "ac_level": selected_automobile_ac.get(),
        "loudness_mode": selected_automobile_loudness.get(),
    }


def automobile_environment_is_active():
    """Return True when automobile simulation should be applied."""
    settings = build_automobile_environment_settings()
    return settings["enabled"]


def ensure_conditioned_trial_files(source_file, noise_seed):
    """Render conditioned source and modified files with matching noise seed."""
    if not automobile_environment_is_active():
        return

    settings = build_automobile_environment_settings()
    create_automobile_conditioned_audio(
        source_file,
        trial_reference_file,
        environment_settings=settings,
        noise_seed=noise_seed,
    )
    create_automobile_conditioned_audio(
        modified_file,
        trial_modified_file,
        environment_settings=settings,
        noise_seed=noise_seed,
    )


def clear_conditioned_trial_files():
    """Remove rendered automobile-conditioned trial files if they exist."""
    for conditioned_file in [trial_reference_file, trial_modified_file]:
        if os.path.exists(conditioned_file):
            os.remove(conditioned_file)


def invalidate_conditioned_trial_audio(*_):
    """Drop conditioned files so next trial/playback uses current automobile settings."""
    clear_conditioned_trial_files()


def apply_automobile_preset():
    """Apply one-click automobile profile to all automobile controls."""
    preset_name = selected_automobile_preset.get()
    preset_settings = AUTOMOBILE_PRESET_SETTINGS.get(preset_name)
    if not preset_settings:
        set_feedback("Choose a valid automobile preset first.", MUTED_TEXT_COLOR)
        return

    selected_automobile_monitoring.set(preset_settings["monitoring"])
    selected_automobile_cabin.set(preset_settings["cabin"])
    selected_automobile_ac.set(preset_settings["ac"])
    selected_automobile_loudness.set(preset_settings["loudness"])
    sync_automobile_control_states()
    set_feedback(f"Applied automobile preset: {preset_name}.", MUTED_TEXT_COLOR)


def update_status_label():
    """Render selected controls, lock states, and active trial values."""
    if "status_label" not in globals():
        # During startup, traces can fire before status_label is created.
        return

    selected_file_name = os.path.basename(reference_file) if reference_file else "None"

    selected_state = (
        f"File={selected_file_name} | "
        f"Section={get_section_status_text()} | "
        f"Test={selected_test_mode.get()} | "
        f"NoChange={format_no_change_rate_for_status()} | "
        f"AutoMon={selected_automobile_monitoring.get()} | "
        f"Cabin={selected_automobile_cabin.get()} | "
        f"AC={selected_automobile_ac.get()} | "
        f"Loudness={selected_automobile_loudness.get()} | "
        f"Mode={selected_randomization_mode.get()} | "
        f"Band={selected_band_mode.get()} | "
        f"FreqRange={selected_range_min.get()}-{selected_range_max.get()} Hz | "
        f"Cuts={selected_cut_count.get()} | "
        f"Boosts={selected_boost_count.get()} | "
        f"GainMode={selected_gain_direction.get()} | "
        f"CutRange={selected_cut_min.get()}..{selected_cut_max.get()} dB | "
        f"ExactCut={selected_exact_cut.get()} dB | "
        f"BoostRange={selected_boost_min.get()}..{selected_boost_max.get()} dB | "
        f"ExactBoost={selected_exact_boost.get()} dB | "
        f"Freq={selected_frequency.get()} Hz | "
        f"Gain={selected_gain.get()} dB | "
        f"Q={format_value_for_status(selected_q.get())}"
    )
    lock_state = (
        f"Locks: Band={'On' if lock_band_mode.get() else 'Off'}, "
        f"Range={'On' if lock_range.get() else 'Off'}, "
        f"Freq={'On' if lock_frequency.get() else 'Off'}, "
        f"Gain={'On' if lock_gain.get() else 'Off'}, "
        f"ExactCut={'On' if lock_exact_cut.get() else 'Off'}, "
        f"ExactBoost={'On' if lock_exact_boost.get() else 'Off'}, "
        f"Q={'On' if lock_q.get() else 'Off'}"
    )

    if current_trial_has_change is None:
        trial_state = "Current Trial: not generated yet"
    else:
        trial_state = "Current Trial: ready for listening"

    practice_state = f"Response: {last_feedback}"

    status_text = "\n".join([
        "Live Status",
        selected_state,
        lock_state,
        trial_state,
        practice_state,
    ])
    status_label.config(text=status_text)

    if "selected_file_label" in globals():
        selected_file_label.config(text=f"Selected File: {selected_file_name}")


def get_identification_value_options():
    """Return answer options for mode 2 based on the selected target."""
    target = selected_identification_target.get()
    if target == "Frequency":
        return get_frequency_options(selected_band_mode.get())
    if target == "Q":
        return Q_OPTIONS
    return GAIN_OPTIONS


def get_expected_identification_answers():
    """Return the correct answer list for the current mode-2 target."""
    target = selected_identification_target.get()
    if target == "Frequency":
        return [change["frequency"] for change in current_filters]
    if target == "Q":
        return [change["q"] for change in current_filters]
    return [change["gain"] for change in current_filters]


def normalize_answer_values(values):
    """Normalize mixed int/float answers for stable comparison and display."""
    normalized = []
    for value in values:
        if isinstance(value, float) and value.is_integer():
            normalized.append(int(value))
        else:
            normalized.append(value)
    return normalized


def set_feedback(message, color=TEXT_COLOR):
    """Update visible response feedback and mirror it into live status."""
    global last_feedback

    last_feedback = message
    feedback_label.config(text=message, fg=color)
    update_status_label()


def get_section_status_text():
    """Return a compact source-section label for live status."""
    if selected_section_start_seconds is None or selected_section_end_seconds is None:
        return "Full"

    return f"{selected_section_start_seconds:.2f}-{selected_section_end_seconds:.2f}s"


def get_session_summary_lines():
    """Build lightweight session stats for the current run."""
    total_trials = sum(1 for event in session_events if event.get("event_type") == "trial_created")
    total_answers = len(session_results)
    correct_answers = sum(1 for result in session_results if result["correct"])

    mode1_results = [result for result in session_results if result["test_mode"] == TEST_MODE_OPTIONS[0]]
    mode2_results = [result for result in session_results if result["test_mode"] == TEST_MODE_OPTIONS[1]]

    hits = sum(1 for result in mode1_results if result["outcome"] == "hit")
    misses = sum(1 for result in mode1_results if result["outcome"] == "miss")
    false_alarms = sum(1 for result in mode1_results if result["outcome"] == "false_alarm")
    correct_rejects = sum(1 for result in mode1_results if result["outcome"] == "correct_reject")

    mode2_partial = sum(result.get("matched_count", 0) for result in mode2_results)
    mode2_total_targets = sum(result.get("target_count", 0) for result in mode2_results)

    accuracy_text = "n/a" if total_answers == 0 else f"{round((correct_answers / total_answers) * 100)}%"
    mode2_match_text = "n/a"
    if mode2_total_targets:
        mode2_match_text = f"{mode2_partial}/{mode2_total_targets}"

    return [
        "Session Stats",
        f"Trials Created: {total_trials}",
        f"Answered: {total_answers} | Correct: {correct_answers} | Accuracy: {accuracy_text}",
        f"Detection: Hits={hits}, Misses={misses}, False Alarms={false_alarms}, Correct Rejects={correct_rejects}",
        f"Identification: Trials={len(mode2_results)}, Matched Targets={mode2_match_text}",
    ]


def get_score_display_text():
    """Return score text in correct/answered form with accuracy percentage."""
    total_answers = len(session_results)
    correct_answers = sum(1 for result in session_results if result["correct"])
    accuracy = 0 if total_answers == 0 else round((correct_answers / total_answers) * 100)
    return f"Current Score: {correct_answers}/{total_answers} ({accuracy}%)"


def update_session_stats_label():
    """Refresh the visible session stats summary."""
    if "session_stats_label" in globals():
        session_stats_label.config(text="\n".join(get_session_summary_lines()))

    if "score_label" in globals():
        score_label.config(text=get_score_display_text())


def build_current_trial_result_base():
    """Capture common trial metadata for session logging/export."""
    tested_frequencies = [str(change.get("frequency", "")) for change in current_filters if "frequency" in change]
    tested_gains = [str(change.get("gain", "")) for change in current_filters if "gain" in change]
    tested_q_values = [str(change.get("q", "")) for change in current_filters if "q" in change]

    return {
        "trial_id": current_trial_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "test_mode": selected_test_mode.get(),
        "identification_target": selected_identification_target.get(),
        "band_mode": current_band_mode,
        "gain_direction": selected_gain_direction.get(),
        "randomization_mode": selected_randomization_mode.get(),
        "automobile_monitoring": selected_automobile_monitoring.get(),
        "automobile_cabin": selected_automobile_cabin.get(),
        "automobile_ac": selected_automobile_ac.get(),
        "automobile_loudness": selected_automobile_loudness.get(),
        "has_change": current_trial_has_change,
        "filter_count": len(current_filters),
        "tested_frequencies": "|".join(tested_frequencies),
        "tested_gains": "|".join(tested_gains),
        "tested_q_values": "|".join(tested_q_values),
        "filters": repr(current_filters),
        "feedback": last_feedback,
    }


def _score_ratio_parts(result):
    """Return matched/total parts from score detail for weighted analytics."""
    score_detail = str(result.get("score_detail", "")).strip()
    if "/" in score_detail:
        left, right = score_detail.split("/", 1)
        try:
            matched = int(left)
            total = int(right)
            if total > 0:
                return matched, total
        except ValueError:
            pass

    return (1, 1) if result.get("correct") else (0, 1)


def _parse_pipe_values(raw_value):
    """Split pipe-delimited values emitted in exported result metadata."""
    if not raw_value:
        return []

    return [token for token in str(raw_value).split("|") if token]


def _format_percent(numerator, denominator):
    """Render percentage text with one decimal point."""
    if denominator <= 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.1f}%"


def build_session_analysis_rows(results):
    """Build summary/analysis rows appended after detailed session rows."""
    if not results:
        return []

    total_attempts = len(results)
    total_correct = sum(1 for result in results if result.get("correct"))
    total_matched = 0
    total_targets = 0
    for result in results:
        matched, targets = _score_ratio_parts(result)
        total_matched += matched
        total_targets += targets

    rows = [
        {
            "analysis_section": "overall",
            "analysis_label": "total_success_rate",
            "analysis_value": _format_percent(total_correct, total_attempts),
            "analysis_success_rate": _format_percent(total_correct, total_attempts),
            "analysis_attempts": total_attempts,
            "analysis_correct": total_correct,
        },
        {
            "analysis_section": "overall",
            "analysis_label": "total_parameter_match_rate",
            "analysis_value": _format_percent(total_matched, total_targets),
            "analysis_success_rate": _format_percent(total_matched, total_targets),
            "analysis_attempts": total_targets,
            "analysis_correct": total_matched,
        },
    ]

    frequency_stats = {}
    parameter_groups = {
        "mode": {},
        "identification_target": {},
        "band_mode": {},
        "gain_direction": {},
        "filter_count": {},
        "has_change": {},
        "automobile_monitoring": {},
        "automobile_cabin": {},
        "automobile_ac": {},
        "automobile_loudness": {},
        "tested_gain": {},
        "tested_q": {},
    }

    def update_bucket(container, bucket_key, trial_correct, trial_matched, trial_targets):
        if bucket_key in {None, "", "None"}:
            return
        bucket = container.setdefault(
            str(bucket_key),
            {"attempts": 0, "correct": 0, "matched": 0, "targets": 0},
        )
        bucket["attempts"] += 1
        bucket["correct"] += 1 if trial_correct else 0
        bucket["matched"] += trial_matched
        bucket["targets"] += trial_targets

    for result in results:
        trial_correct = bool(result.get("correct"))
        trial_matched, trial_targets = _score_ratio_parts(result)

        for frequency in _parse_pipe_values(result.get("tested_frequencies")):
            update_bucket(frequency_stats, frequency, trial_correct, trial_matched, trial_targets)

        mode_label = "Mode 1" if result.get("test_mode") == TEST_MODE_OPTIONS[0] else "Mode 2"
        update_bucket(parameter_groups["mode"], mode_label, trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["identification_target"], result.get("identification_target"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["band_mode"], result.get("band_mode"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["gain_direction"], result.get("gain_direction"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["filter_count"], result.get("filter_count"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["has_change"], result.get("has_change"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["automobile_monitoring"], result.get("automobile_monitoring"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["automobile_cabin"], result.get("automobile_cabin"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["automobile_ac"], result.get("automobile_ac"), trial_correct, trial_matched, trial_targets)
        update_bucket(parameter_groups["automobile_loudness"], result.get("automobile_loudness"), trial_correct, trial_matched, trial_targets)

        for gain_value in _parse_pipe_values(result.get("tested_gains")):
            update_bucket(parameter_groups["tested_gain"], gain_value, trial_correct, trial_matched, trial_targets)
        for q_value in _parse_pipe_values(result.get("tested_q_values")):
            update_bucket(parameter_groups["tested_q"], q_value, trial_correct, trial_matched, trial_targets)

    sorted_frequency_items = sorted(
        frequency_stats.items(),
        key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]),
    )

    for frequency_label, stats in sorted_frequency_items:
        rows.append(
            {
                "analysis_section": "frequency",
                "analysis_label": f"{frequency_label} Hz",
                "analysis_value": _format_percent(stats["matched"], stats["targets"]),
                "analysis_success_rate": _format_percent(stats["correct"], stats["attempts"]),
                "analysis_attempts": stats["attempts"],
                "analysis_correct": stats["correct"],
            }
        )

    frequency_rank = sorted(
        sorted_frequency_items,
        key=lambda item: (
            (item[1]["correct"] / item[1]["attempts"]) if item[1]["attempts"] else 0,
            item[1]["attempts"],
        ),
    )
    if frequency_rank:
        weakest_frequency = frequency_rank[0]
        strongest_frequency = frequency_rank[-1]
        rows.append(
            {
                "analysis_section": "frequency",
                "analysis_label": "strengths_vs_weaknesses",
                "analysis_strength": (
                    f"Strongest: {strongest_frequency[0]} Hz "
                    f"({_format_percent(strongest_frequency[1]['correct'], strongest_frequency[1]['attempts'])}, "
                    f"{strongest_frequency[1]['correct']}/{strongest_frequency[1]['attempts']})"
                ),
                "analysis_weakness": (
                    f"Weakest: {weakest_frequency[0]} Hz "
                    f"({_format_percent(weakest_frequency[1]['correct'], weakest_frequency[1]['attempts'])}, "
                    f"{weakest_frequency[1]['correct']}/{weakest_frequency[1]['attempts']})"
                ),
            }
        )

    for group_name, buckets in parameter_groups.items():
        if not buckets:
            continue

        sorted_items = sorted(
            buckets.items(),
            key=lambda item: (
                (item[1]["correct"] / item[1]["attempts"]) if item[1]["attempts"] else 0,
                item[1]["attempts"],
            ),
        )

        for bucket_label, stats in sorted(
            buckets.items(),
            key=lambda item: str(item[0]),
        ):
            rows.append(
                {
                    "analysis_section": f"parameter:{group_name}",
                    "analysis_label": str(bucket_label),
                    "analysis_value": _format_percent(stats["matched"], stats["targets"]),
                    "analysis_success_rate": _format_percent(stats["correct"], stats["attempts"]),
                    "analysis_attempts": stats["attempts"],
                    "analysis_correct": stats["correct"],
                }
            )

        weakest_item = sorted_items[0]
        strongest_item = sorted_items[-1]
        rows.append(
            {
                "analysis_section": f"parameter:{group_name}",
                "analysis_label": "strengths_vs_weaknesses",
                "analysis_strength": (
                    f"Strongest: {strongest_item[0]} "
                    f"({_format_percent(strongest_item[1]['correct'], strongest_item[1]['attempts'])}, "
                    f"{strongest_item[1]['correct']}/{strongest_item[1]['attempts']})"
                ),
                "analysis_weakness": (
                    f"Weakest: {weakest_item[0]} "
                    f"({_format_percent(weakest_item[1]['correct'], weakest_item[1]['attempts'])}, "
                    f"{weakest_item[1]['correct']}/{weakest_item[1]['attempts']})"
                ),
            }
        )

    return rows


def record_session_event(event_type, details=None):
    """Append a session-level event to support richer export history."""
    event = build_current_trial_result_base()
    event["event_type"] = event_type
    if details:
        event.update(details)

    session_events.append(event)
    update_session_stats_label()


def record_session_result(result):
    """Append a scored response to the session log and refresh stats."""
    global current_trial_scored

    record_session_event("trial_answered", dict(result))
    session_results.append(result)
    current_trial_scored = True
    update_session_stats_label()


def reset_session_stats():
    """Clear the in-memory session results and refresh the summary."""
    global session_results
    global session_events

    session_results = []
    session_events = []
    update_session_stats_label()
    set_feedback("Session stats reset.", MUTED_TEXT_COLOR)


def start_new_session():
    """Reset stats and remove generated study/match audio for a clean session."""
    reset_session_stats()

    removed_files = []
    for generated_file in [
        modified_file,
        match_file,
        memorization_file,
        selected_section_file,
        trial_reference_file,
        trial_modified_file,
    ]:
        if os.path.exists(generated_file):
            os.remove(generated_file)
            removed_files.append(os.path.basename(generated_file))

    if removed_files:
        set_feedback(
            f"Started new session. Cleared stats and removed {', '.join(removed_files)}.",
            MUTED_TEXT_COLOR,
        )
    else:
        set_feedback("Started new session. Cleared stats.", MUTED_TEXT_COLOR)


def export_session_results():
    """Export current session results to a CSV file."""
    if not session_results:
        set_feedback("No session results to export yet.", MUTED_TEXT_COLOR)
        return

    export_dir = os.path.join(os.path.dirname(__file__), SESSION_EXPORT_DIR)
    os.makedirs(export_dir, exist_ok=True)

    default_name = f"listening_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    export_path = filedialog.asksaveasfilename(
        title="Export Session Results",
        defaultextension=".csv",
        initialdir=export_dir,
        initialfile=default_name,
        filetypes=[("CSV Files", "*.csv")],
    )

    if not export_path:
        return

    fieldnames = [
        "trial_id",
        "timestamp",
        "mode",
        "score_detail",
        "correct",
        "outcome",
        "user_response",
        "expected_response",
        "matched_count",
        "target_count",
        "identification_target",
        "band_mode",
        "gain_direction",
        "randomization_mode",
        "automobile_monitoring",
        "automobile_cabin",
        "automobile_ac",
        "automobile_loudness",
        "has_change",
        "filter_count",
        "tested_frequencies",
        "tested_gains",
        "tested_q_values",
        "feedback",
        "analysis_section",
        "analysis_label",
        "analysis_value",
        "analysis_success_rate",
        "analysis_attempts",
        "analysis_correct",
        "analysis_strength",
        "analysis_weakness",
    ]

    export_rows = []
    for result in session_results:
        mode_text = result.get("test_mode", "")
        is_mode_1 = mode_text == TEST_MODE_OPTIONS[0]
        export_rows.append(
            {
                "trial_id": result.get("trial_id", ""),
                "timestamp": result.get("timestamp", ""),
                "mode": "Mode 1" if is_mode_1 else "Mode 2",
                "score_detail": result.get("score_detail", ""),
                "correct": result.get("correct", ""),
                "outcome": result.get("outcome", ""),
                "user_response": result.get("user_response", ""),
                "expected_response": result.get("expected_response", ""),
                "matched_count": "" if is_mode_1 else result.get("matched_count", ""),
                "target_count": "" if is_mode_1 else result.get("target_count", ""),
                "identification_target": "" if is_mode_1 else result.get("identification_target", ""),
                "band_mode": result.get("band_mode", ""),
                "gain_direction": result.get("gain_direction", ""),
                "randomization_mode": result.get("randomization_mode", ""),
                "automobile_monitoring": result.get("automobile_monitoring", ""),
                "automobile_cabin": result.get("automobile_cabin", ""),
                "automobile_ac": result.get("automobile_ac", ""),
                "automobile_loudness": result.get("automobile_loudness", ""),
                "has_change": result.get("has_change", ""),
                "filter_count": result.get("filter_count", ""),
                "tested_frequencies": result.get("tested_frequencies", ""),
                "tested_gains": result.get("tested_gains", ""),
                "tested_q_values": result.get("tested_q_values", ""),
                "feedback": result.get("feedback", ""),
            }
        )

    analysis_rows = build_session_analysis_rows(session_results)


    try:
        with open(export_path, "w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            if analysis_rows:
                writer.writerow({})
                writer.writerows(analysis_rows)
            writer.writerows(export_rows)
    except OSError as exc:
        set_feedback(f"Export failed: {exc}", "firebrick")
        return

    set_feedback(f"Exported session results to {os.path.basename(export_path)}.")


def on_app_close():
    """Ensure playback stops and runtime artifacts are cleaned up on close."""
    stop_audio()
    cleanup_runtime_audio_dir()
    root.destroy()


def get_active_filter_count():
    """Return the number of answers mode 2 should currently display."""
    if current_filters:
        return len(current_filters)

    return max(1, selected_cut_count.get() + selected_boost_count.get())


def update_identification_value_menu(*_):
    """Keep the mode-2 answer dropdowns aligned with the selected target."""
    value_options = get_identification_value_options()
    for answer_var, answer_menu in zip(identification_answer_vars, identification_value_menus):
        refresh_option_menu(answer_menu, answer_var, value_options)

        if answer_var.get() not in value_options:
            answer_var.set(value_options[0])


def update_identification_answer_rows():
    """Show one answer selector per active filter, up to three total."""
    active_count = min(MAX_FILTERS_PER_TRIAL, get_active_filter_count())
    target = selected_identification_target.get()
    detection_mode = selected_test_mode.get() == TEST_MODE_OPTIONS[0]

    if active_count == 1:
        identification_prompt_label.config(text=f"Answer Value ({target}):")
    else:
        identification_prompt_label.config(text=f"Answer Values ({target}, choose {active_count}):")

    for index, answer_row in enumerate(identification_answer_rows, start=1):
        if not detection_mode and index <= active_count:
            answer_row.pack(anchor="w", padx=30, pady=(0, 6 if index < active_count else 12))
            set_option_menu_state(identification_value_menus[index - 1], "normal")
            set_label_state(identification_answer_labels[index - 1], True)
        else:
            answer_row.pack_forget()

    update_identification_value_menu()


def set_identification_submit_enabled(enabled):
    """Enable submit/check button for mode-2 answers after user edits."""
    if "check_answers_button" not in globals():
        return

    check_answers_button.config(state="normal" if enabled else "disabled")


def select_detection_answer(user_detected_change):
    """Store a mode-1 answer choice and enable explicit submit."""
    global pending_detection_answer

    pending_detection_answer = user_detected_change

    if "mode1_selected_answer_label" in globals():
        choice_text = "Yes" if user_detected_change else "No"
        mode1_selected_answer_label.config(text=f"Selected: {choice_text}", fg=TEXT_COLOR)

    if "submit_detection_button" in globals():
        submit_detection_button.config(state="normal")

    set_feedback("Answer selected. Click Submit Answer to score.", MUTED_TEXT_COLOR)


def submit_detection_answer():
    """Submit stored mode-1 choice for scoring."""
    if pending_detection_answer is None:
        set_feedback("Select Yes or No before submitting.", MUTED_TEXT_COLOR)
        return

    check_detection_response(pending_detection_answer)


def reset_pending_detection_answer():
    """Clear mode-1 pending choice and disable submit."""
    global pending_detection_answer

    pending_detection_answer = None
    if "mode1_selected_answer_label" in globals():
        mode1_selected_answer_label.config(text="Selected: none", fg=MUTED_TEXT_COLOR)
    if "submit_detection_button" in globals():
        submit_detection_button.config(state="disabled")


def on_identification_answer_changed(*_):
    """Arm mode-2 submit when user changes an answer choice."""
    if selected_test_mode.get() == TEST_MODE_OPTIONS[1]:
        set_identification_submit_enabled(True)


def update_response_mode(*_):
    """Switch the response prompt and controls between test modes."""
    detection_mode = selected_test_mode.get() == TEST_MODE_OPTIONS[0]

    if detection_mode:
        answer_label.config(text="Do Sample A and Sample B sound different?")
        set_option_menu_state(no_change_rate_menu, "normal")
        set_label_state(no_change_rate_label, True)
        set_label_state(mode1_options_label, True)

        set_option_menu_state(identification_target_menu, "disabled")
        set_label_state(identification_target_label, False)
        set_label_state(mode2_options_label, False)
        identification_prompt_label.pack_forget()
        for answer_row in identification_answer_rows:
            answer_row.pack_forget()
        check_answers_button.pack_forget()
        mode1_selected_answer_label.pack(anchor="w", padx=30, pady=(0, 4))
        submit_detection_button.pack(anchor="w", padx=30, pady=(0, 12))
        yes_no_button_frame.pack(anchor="w", padx=30, pady=(0, 12))
        set_identification_submit_enabled(False)
    else:
        answer_label.config(text="Which specific settings changed in the trial?")
        yes_no_button_frame.pack_forget()
        mode1_selected_answer_label.pack_forget()
        submit_detection_button.pack_forget()
        set_option_menu_state(no_change_rate_menu, "disabled")
        set_label_state(no_change_rate_label, False)
        set_label_state(mode1_options_label, False)

        set_option_menu_state(identification_target_menu, "normal")
        set_label_state(identification_target_label, True)
        set_label_state(mode2_options_label, True)
        identification_prompt_label.pack(anchor="w", padx=30, pady=(0, 4))
        update_identification_answer_rows()
        check_answers_button.pack(anchor="w", padx=30, pady=(0, 12))
        set_identification_submit_enabled(False)

    update_status_label()


def check_detection_response(user_detected_change):
    """Score mode-1 yes/no responses against the current trial state."""
    if current_trial_has_change is None:
        set_feedback("Create a trial before checking an answer.", MUTED_TEXT_COLOR)
        return
    if current_trial_scored:
        set_feedback("This trial was already scored. Create a new trial to continue.", MUTED_TEXT_COLOR)
        return

    result = build_current_trial_result_base()
    result["user_response"] = "yes" if user_detected_change else "no"
    result["expected_response"] = "yes" if current_trial_has_change else "no"
    if user_detected_change == current_trial_has_change:
        if current_trial_has_change:
            set_feedback("Correct: there is a change in this trial.")
            result["outcome"] = "hit"
        else:
            set_feedback("Correct: this trial contains no change.")
            result["outcome"] = "correct_reject"
        result["correct"] = True
    else:
        if current_trial_has_change:
            set_feedback("Incorrect: this trial does contain a change.", "firebrick")
            result["outcome"] = "miss"
        else:
            set_feedback("Incorrect: this trial contains no change.", "firebrick")
            result["outcome"] = "false_alarm"
        result["correct"] = False

    result["score_detail"] = "1/1" if result["correct"] else "0/1"
    result["feedback"] = last_feedback
    record_session_result(result)
    reset_pending_detection_answer()


def check_identification_response():
    """Score multi-answer mode-2 responses using unordered set matching."""
    if not current_filters:
        set_feedback("Create a trial before checking an answer.", MUTED_TEXT_COLOR)
        return
    if current_trial_scored:
        set_feedback("This trial was already scored. Create a new trial to continue.", MUTED_TEXT_COLOR)
        return

    answer_count = len(current_filters)
    expected_answers = normalize_answer_values(get_expected_identification_answers())
    user_answers = normalize_answer_values(
        [answer_var.get() for answer_var in identification_answer_vars[:answer_count]]
    )

    expected_sorted = sorted(expected_answers)
    user_sorted = sorted(user_answers)
    correct_matches = sum(
        1 for expected, actual in zip(expected_sorted, user_sorted) if expected == actual
    )

    result = build_current_trial_result_base()
    result["user_response"] = repr(user_sorted)
    result["expected_response"] = repr(expected_sorted)
    result["matched_count"] = correct_matches
    result["target_count"] = answer_count
    result["score_detail"] = f"{correct_matches}/{answer_count}"
    result["correct"] = user_sorted == expected_sorted
    if result["correct"]:
        result["outcome"] = "full_match"
    elif correct_matches > 0:
        result["outcome"] = "partial_match"
    else:
        result["outcome"] = "no_match"

    if user_sorted == expected_sorted:
        set_feedback(f"Correct: matched all {answer_count} answers.")
    else:
        set_feedback(
            f"Incorrect: matched {correct_matches}/{answer_count}. Expected {expected_sorted}.",
            "firebrick",
        )

    result["feedback"] = last_feedback
    record_session_result(result)


def build_memorization_filters():
    """Create a deterministic study example from the current control settings."""
    selected_values = {
        "band_mode": selected_band_mode.get(),
        "range_min": selected_range_min.get(),
        "range_max": selected_range_max.get(),
        "gain_direction": selected_gain_direction.get(),
        "cut_count": selected_cut_count.get(),
        "boost_count": selected_boost_count.get(),
        "cut_min": selected_cut_min.get(),
        "cut_max": selected_cut_max.get(),
        "boost_min": selected_boost_min.get(),
        "boost_max": selected_boost_max.get(),
        "exact_cut": selected_exact_cut.get(),
        "exact_boost": selected_exact_boost.get(),
        "frequency": selected_frequency.get(),
        "gain": selected_gain.get(),
        "q": selected_q.get(),
    }
    lock_values = {
        "band_mode": True,
        "range": True,
        "frequency": True,
        "gain": True,
        "exact_cut": lock_exact_cut.get(),
        "exact_boost": lock_exact_boost.get(),
        "q": True,
    }
    return resolve_trial_parameters(selected_values, lock_values, "Use Selected Values")["filters"]


def build_match_filters_from_answers():
    """Create comparison filters by swapping in the user's guessed values."""
    if not current_filters:
        return []

    target = selected_identification_target.get()
    guessed_values = [
        identification_answer_vars[index].get()
        for index in range(len(current_filters))
    ]

    guessed_filters = []
    for filter_settings, guessed_value in zip(current_filters, guessed_values):
        guessed_filter = dict(filter_settings)
        if target == "Frequency":
            guessed_filter["frequency"] = guessed_value
        elif target == "Q":
            guessed_filter["q"] = guessed_value
        else:
            guessed_filter["gain"] = guessed_value
        guessed_filters.append(guessed_filter)

    return guessed_filters


def render_memorization_audio():
    """Render a study example using the current selected controls."""
    study_filters = build_memorization_filters()
    source_file = prepare_selected_source_file()
    if not source_file:
        return
    environment_settings = build_automobile_environment_settings() if automobile_environment_is_active() else None
    create_modified_audio(
        source_file,
        memorization_file,
        study_filters,
        environment_settings=environment_settings,
        noise_seed=current_trial_id,
    )
    set_feedback("Reference example rendered from your current settings.")


def play_memorization_audio():
    """Play the rendered memorization example, creating it if needed."""
    if not os.path.exists(memorization_file):
        render_memorization_audio()
    play_audio_file(memorization_file)


def render_match_audio():
    """Render the user's current answer guess as a comparison signal."""
    guessed_filters = build_match_filters_from_answers()
    if not guessed_filters:
        set_feedback("Create a trial before rendering a match guess.", MUTED_TEXT_COLOR)
        return

    source_file = prepare_selected_source_file()
    if not source_file:
        return
    environment_settings = build_automobile_environment_settings() if automobile_environment_is_active() else None
    create_modified_audio(
        source_file,
        match_file,
        guessed_filters,
        environment_settings=environment_settings,
        noise_seed=current_trial_id,
    )
    set_feedback("Your answer guess example was rendered for comparison.")


def play_match_audio():
    """Play the rendered answer-match example, creating it if needed."""
    if not current_filters:
        set_feedback("Create a trial before using match mode.", MUTED_TEXT_COLOR)
        return

    if not os.path.exists(match_file):
        render_match_audio()
    play_audio_file(match_file)


def normalize_section_bounds(start_seconds, end_seconds, clip_duration):
    """Return ordered, clipped section boundaries in seconds."""
    start_value = max(0.0, min(start_seconds, clip_duration))
    end_value = max(0.0, min(end_seconds, clip_duration))
    if end_value < start_value:
        start_value, end_value = end_value, start_value
    return start_value, end_value


def update_section_info_label(extra_text=""):
    """Refresh text shown under the waveform section picker."""
    if "waveform_selection_label" not in globals():
        return

    if waveform_mono_data is None:
        waveform_selection_label.config(text="No waveform loaded.")
        return

    if selected_section_start_seconds is None or selected_section_end_seconds is None:
        text = (
            f"Using full file ({waveform_duration_seconds:.2f}s). "
            "Click waveform once for start and again for end."
        )
    else:
        section_length = max(0.0, selected_section_end_seconds - selected_section_start_seconds)
        text = (
            f"Selected {selected_section_start_seconds:.2f}s to "
            f"{selected_section_end_seconds:.2f}s ({section_length:.2f}s)."
        )

    if extra_text:
        text = f"{text} {extra_text}"

    waveform_selection_label.config(text=text)


def draw_waveform_canvas():
    """Render waveform preview with selected-section overlay."""
    if "waveform_canvas" not in globals():
        return

    waveform_canvas.delete("all")

    canvas_width = int(waveform_canvas.cget("width"))
    canvas_height = int(waveform_canvas.cget("height"))
    center_y = canvas_height // 2

    waveform_canvas.create_rectangle(
        0,
        0,
        canvas_width,
        canvas_height,
        fill="#f7f7f7",
        outline="#d8d8d8",
    )
    waveform_canvas.create_line(0, center_y, canvas_width, center_y, fill="#c9c9c9")

    if waveform_mono_data is None or waveform_mono_data.size == 0:
        waveform_canvas.create_text(
            canvas_width // 2,
            center_y,
            text="Load an audio file to view waveform",
            fill="#7a7a7a",
        )
        return

    stride = max(1, int(np.ceil(waveform_mono_data.size / canvas_width)))
    reduced = waveform_mono_data[::stride]
    if reduced.size < canvas_width:
        reduced = np.pad(reduced, (0, canvas_width - reduced.size), mode="edge")
    else:
        reduced = reduced[:canvas_width]

    peak = float(np.max(np.abs(reduced)))
    if peak <= 0.0:
        peak = 1.0

    points = []
    scale = (canvas_height * 0.45) / peak
    for x_index, sample in enumerate(reduced):
        y = center_y - (sample * scale)
        points.extend([x_index, y])

    waveform_canvas.create_line(*points, fill="#2f5d8a", width=1)

    if selected_section_start_seconds is not None and selected_section_end_seconds is not None and waveform_duration_seconds > 0:
        x1 = (selected_section_start_seconds / waveform_duration_seconds) * canvas_width
        x2 = (selected_section_end_seconds / waveform_duration_seconds) * canvas_width
        waveform_canvas.create_rectangle(
            x1,
            0,
            x2,
            canvas_height,
            fill="#7dc8ff",
            stipple="gray25",
            outline="#1a6aa8",
            width=2,
        )


def load_reference_waveform_data():
    """Load waveform data from the selected source file."""
    global waveform_mono_data
    global waveform_sample_rate
    global waveform_duration_seconds
    global selected_section_start_seconds
    global selected_section_end_seconds

    try:
        audio_data, sample_rate = sf.read(reference_file)
    except Exception as exc:
        waveform_mono_data = None
        waveform_sample_rate = None
        waveform_duration_seconds = 0.0
        selected_section_start_seconds = None
        selected_section_end_seconds = None
        draw_waveform_canvas()
        update_section_info_label(f"Unable to load waveform: {exc}")
        return False

    if audio_data.ndim == 1:
        waveform_mono_data = audio_data.astype(float)
    else:
        waveform_mono_data = np.mean(audio_data, axis=1).astype(float)

    waveform_sample_rate = int(sample_rate)
    if waveform_sample_rate > 0:
        waveform_duration_seconds = float(waveform_mono_data.size) / waveform_sample_rate
    else:
        waveform_duration_seconds = 0.0

    selected_section_start_seconds = None
    selected_section_end_seconds = None
    draw_waveform_canvas()
    update_section_info_label("Using full file.")
    return True


def clear_section_selection():
    """Reset section selection to use the full source file."""
    global selected_section_start_seconds
    global selected_section_end_seconds

    selected_section_start_seconds = None
    selected_section_end_seconds = None
    reset_trial_for_source_update()
    draw_waveform_canvas()
    update_section_info_label("Using full file.")
    update_status_label()


def reset_trial_for_source_update():
    """Clear stale trial audio/state after source file or section changes."""
    global modified_sample
    global current_frequency
    global current_gain
    global current_q
    global current_band_mode
    global current_filters
    global current_trial_has_change
    global current_trial_scored

    modified_sample = None
    current_frequency = None
    current_gain = None
    current_q = None
    current_band_mode = None
    current_filters = []
    current_trial_has_change = None
    current_trial_scored = False

    if os.path.exists(modified_file):
        os.remove(modified_file)

    clear_conditioned_trial_files()

    reset_pending_detection_answer()
    set_identification_submit_enabled(False)
    update_identification_answer_rows()


def _set_auto_select_running(is_running):
    """Toggle UI state while async loud-section search is in progress."""
    global auto_select_running

    auto_select_running = is_running
    if "auto_pick_section_button" in globals():
        auto_pick_section_button.config(state="disabled" if is_running else "normal")


def _animate_auto_select_spinner():
    """Animate progress text while loud-section search runs in background."""
    global auto_select_spinner_after_id
    global auto_select_spinner_index

    if not auto_select_running:
        auto_select_spinner_after_id = None
        return

    frame = auto_select_spinner_frames[auto_select_spinner_index % len(auto_select_spinner_frames)]
    auto_select_spinner_index += 1
    update_section_info_label(f"Finding loud section... {frame}")
    auto_select_spinner_after_id = root.after(120, _animate_auto_select_spinner)


def _start_auto_select_spinner():
    """Start animated progress text for async section auto-pick."""
    global auto_select_spinner_after_id
    global auto_select_spinner_index

    auto_select_spinner_index = 0
    if auto_select_spinner_after_id is not None:
        root.after_cancel(auto_select_spinner_after_id)
        auto_select_spinner_after_id = None
    _animate_auto_select_spinner()


def _stop_auto_select_spinner():
    """Stop animated progress text for async section auto-pick."""
    global auto_select_spinner_after_id

    if auto_select_spinner_after_id is not None:
        root.after_cancel(auto_select_spinner_after_id)
        auto_select_spinner_after_id = None


def _flash_auto_select_done():
    """Briefly highlight completion feedback for auto-pick."""
    global auto_select_done_flash_after_id

    if "waveform_selection_label" not in globals():
        return

    if auto_select_done_flash_after_id is not None:
        root.after_cancel(auto_select_done_flash_after_id)
        auto_select_done_flash_after_id = None

    waveform_selection_label.config(fg="darkgreen")
    update_section_info_label("Auto-selected loud section. [Done]")

    def restore_normal_status():
        global auto_select_done_flash_after_id

        if "waveform_selection_label" not in globals():
            return
        waveform_selection_label.config(fg=MUTED_TEXT_COLOR)
        update_section_info_label("Auto-selected loud section.")
        auto_select_done_flash_after_id = None

    auto_select_done_flash_after_id = root.after(1000, restore_normal_status)


def _find_dense_section_index(samples, sample_rate, section_length_seconds):
    """Return start/end seconds for the loudest section in the provided signal."""
    if samples.size == 0 or sample_rate <= 0:
        return 0.0, 0.0

    window_size = max(1, int(section_length_seconds * sample_rate))
    if window_size >= samples.size:
        duration = float(samples.size) / sample_rate
        return 0.0, duration

    signal = samples.astype(np.float32, copy=False)
    squared = signal * signal
    cumulative = np.concatenate(([0.0], np.cumsum(squared, dtype=np.float64)))

    last_start = samples.size - window_size
    target_checks = 25000
    coarse_hop = max(1, last_start // target_checks)
    coarse_indices = np.arange(0, last_start + 1, coarse_hop, dtype=np.int64)

    coarse_energy = cumulative[coarse_indices + window_size] - cumulative[coarse_indices]
    coarse_best = int(coarse_indices[int(np.argmax(coarse_energy))])

    refine_start = max(0, coarse_best - coarse_hop)
    refine_end = min(last_start, coarse_best + coarse_hop)
    refine_indices = np.arange(refine_start, refine_end + 1, dtype=np.int64)
    refine_energy = cumulative[refine_indices + window_size] - cumulative[refine_indices]
    best_index = int(refine_indices[int(np.argmax(refine_energy))])

    return best_index / sample_rate, (best_index + window_size) / sample_rate


def _apply_dense_section_result(start_seconds, end_seconds):
    """Apply async dense-section result on Tk main thread."""
    global selected_section_start_seconds
    global selected_section_end_seconds

    _stop_auto_select_spinner()
    selected_section_start_seconds, selected_section_end_seconds = normalize_section_bounds(
        start_seconds,
        end_seconds,
        waveform_duration_seconds,
    )

    reset_trial_for_source_update()
    draw_waveform_canvas()
    _flash_auto_select_done()
    update_status_label()
    _set_auto_select_running(False)


def _handle_dense_section_error(error_message):
    """Surface async dense-section failure on Tk main thread."""
    _stop_auto_select_spinner()
    update_section_info_label(f"Auto-select failed: {error_message}")
    set_feedback("Auto-pick loud section failed. Try a different file.", "firebrick")
    _set_auto_select_running(False)


def _run_dense_section_worker(samples_copy, sample_rate, section_length_seconds):
    """Background worker for loud-section detection."""
    try:
        start_seconds, end_seconds = _find_dense_section_index(
            samples_copy,
            sample_rate,
            section_length_seconds,
        )
    except Exception as exc:
        root.after(0, lambda: _handle_dense_section_error(str(exc)))
        return

    root.after(0, lambda: _apply_dense_section_result(start_seconds, end_seconds))


def select_dense_section():
    """Auto-pick a high-energy section using sliding-window energy."""
    global selected_section_start_seconds
    global selected_section_end_seconds
    global auto_select_thread

    if waveform_mono_data is None or waveform_sample_rate is None or waveform_mono_data.size == 0:
        set_feedback("Load a reference file before auto-selecting a section.", MUTED_TEXT_COLOR)
        return

    if auto_select_running:
        set_feedback("Auto-pick is already running.", MUTED_TEXT_COLOR)
        return

    section_length_seconds = float(selected_section_length.get())
    window_size = max(1, int(section_length_seconds * waveform_sample_rate))
    if window_size >= waveform_mono_data.size:
        selected_section_start_seconds = 0.0
        selected_section_end_seconds = waveform_duration_seconds
        reset_trial_for_source_update()
        draw_waveform_canvas()
        update_section_info_label("Clip shorter than selected length; using full file.")
        update_status_label()
        return

    _set_auto_select_running(True)
    _start_auto_select_spinner()
    samples_copy = np.array(waveform_mono_data, copy=True)
    sample_rate = int(waveform_sample_rate)
    auto_select_thread = threading.Thread(
        target=_run_dense_section_worker,
        args=(samples_copy, sample_rate, section_length_seconds),
        daemon=True,
    )
    auto_select_thread.start()


def on_waveform_click(event):
    """Use two clicks to define section start and end positions."""
    global selected_section_start_seconds
    global selected_section_end_seconds

    if waveform_mono_data is None or waveform_duration_seconds <= 0:
        return

    canvas_width = int(waveform_canvas.cget("width"))
    if canvas_width <= 0:
        return

    click_ratio = max(0.0, min(event.x / canvas_width, 1.0))
    click_seconds = click_ratio * waveform_duration_seconds

    if selected_section_start_seconds is None or selected_section_end_seconds is not None:
        selected_section_start_seconds = click_seconds
        selected_section_end_seconds = None
        update_section_info_label("Start set. Click again to set end.")
        draw_waveform_canvas()
        return

    selected_section_start_seconds, selected_section_end_seconds = normalize_section_bounds(
        selected_section_start_seconds,
        click_seconds,
        waveform_duration_seconds,
    )

    if (selected_section_end_seconds - selected_section_start_seconds) < 0.1:
        selected_section_end_seconds = min(waveform_duration_seconds, selected_section_start_seconds + 0.1)

    reset_trial_for_source_update()
    draw_waveform_canvas()
    update_section_info_label("Manual section selected.")
    update_status_label()


def prepare_selected_source_file():
    """Write selected section to disk and return active source audio path."""
    if not reference_file:
        set_feedback("Choose an audio file first.", MUTED_TEXT_COLOR)
        return None

    if (
        selected_section_start_seconds is None
        or selected_section_end_seconds is None
        or waveform_mono_data is None
        or waveform_sample_rate is None
    ):
        return reference_file

    try:
        full_audio, sample_rate = sf.read(reference_file)
    except Exception as exc:
        set_feedback(f"Could not read source file: {exc}", "firebrick")
        return reference_file

    total_samples = full_audio.shape[0]
    start_sample = max(0, int(selected_section_start_seconds * sample_rate))
    end_sample = min(total_samples, int(selected_section_end_seconds * sample_rate))
    if end_sample <= start_sample:
        return reference_file

    sf.write(selected_section_file, full_audio[start_sample:end_sample], sample_rate)
    return selected_section_file


def play_selected_section():
    """Play selected waveform section (or full file when none selected)."""
    source_file = prepare_selected_source_file()
    if not source_file:
        return
    play_audio_file(source_file)

# =========================
# Audio Playback Controls
# =========================
def play_audio_file(filename):
    """Play a file via afplay, replacing any active playback process."""
    global audio_process

    if audio_process is not None:
        audio_process.terminate()

    audio_process = subprocess.Popen(["afplay", filename])


def play_reference():
    """Play the unmodified reference file, replacing any current playback."""
    source_file = prepare_selected_source_file()
    if not source_file:
        return
    play_audio_file(source_file)

def stop_audio():
    """Stop whichever preview process is currently playing."""
    global audio_process

    if audio_process is not None:
        audio_process.terminate()
        audio_process = None


def choose_reference_file():
    """Allow the user to select a source audio file for frequency practice."""
    global reference_file

    selected_file = filedialog.askopenfilename(
        title="Select Reference Audio File",
        filetypes=[
            ("Audio Files", "*.wav *.aif *.aiff *.flac"),
            ("All Files", "*.*"),
        ],
    )

    if not selected_file:
        return

    reference_file = selected_file
    if load_reference_waveform_data():
        reset_trial_for_source_update()
        set_feedback("Loaded file and refreshed waveform preview.", MUTED_TEXT_COLOR)
    update_status_label()


# =========================
# Trial Creation Flow
# =========================
def create_trial():
    """Resolve trial parameters, render modified audio, and refresh GUI state."""
    global modified_sample
    global current_frequency
    global current_gain
    global current_q
    global current_band_mode
    global current_filters
    global current_trial_has_change
    global current_trial_id
    global current_trial_scored

    current_trial_id += 1
    current_trial_scored = False

    selected_values = {
        # GUI-selected values are passed to backend for final resolution.
        "band_mode": selected_band_mode.get(),
        "range_min": selected_range_min.get(),
        "range_max": selected_range_max.get(),
        "gain_direction": selected_gain_direction.get(),
        "cut_count": selected_cut_count.get(),
        "boost_count": selected_boost_count.get(),
        "cut_min": selected_cut_min.get(),
        "cut_max": selected_cut_max.get(),
        "boost_min": selected_boost_min.get(),
        "boost_max": selected_boost_max.get(),
        "exact_cut": selected_exact_cut.get(),
        "exact_boost": selected_exact_boost.get(),
        "frequency": selected_frequency.get(),
        "gain": selected_gain.get(),
        "q": selected_q.get(),
    }
    lock_values = {
        # Lock state controls which values can be randomized or constrained.
        "band_mode": lock_band_mode.get(),
        "range": lock_range.get(),
        "frequency": lock_frequency.get(),
        "gain": lock_gain.get(),
        "exact_cut": lock_exact_cut.get(),
        "exact_boost": lock_exact_boost.get(),
        "q": lock_q.get(),
    }

    source_file = prepare_selected_source_file()
    if not source_file:
        return

    environment_settings = build_automobile_environment_settings() if automobile_environment_is_active() else None
    trial_noise_seed = current_trial_id

    trial_params = create_trial_audio(
        source_file,
        modified_file,
        selected_values,
        lock_values,
        selected_randomization_mode.get(),
        allow_no_change=(selected_test_mode.get() == TEST_MODE_OPTIONS[0]),
        no_change_probability=selected_no_change_rate.get(),
        environment_settings=environment_settings,
        noise_seed=trial_noise_seed,
    )

    if automobile_environment_is_active():
        ensure_conditioned_trial_files(source_file, trial_noise_seed)

    modified_sample = trial_params["modified_sample"]
    current_band_mode = trial_params["band_mode"]
    current_frequency = trial_params["frequency"]
    current_gain = trial_params["gain"]
    current_q = trial_params["q"]
    current_filters = trial_params["filters"]
    current_trial_has_change = trial_params.get("has_change", True)

    # Reflect only trial-wide settings. Per-filter details can vary when counts > 1.
    selected_band_mode.set(current_band_mode)
    if current_trial_has_change and len(current_filters) == 1:
        selected_frequency.set(current_frequency)
        selected_gain.set(current_gain)
        selected_q.set(current_q)

    print("Modified sample:", modified_sample)
    print("Filters:", current_filters)
    print("Has change:", current_trial_has_change)
    print("Band mode:", current_band_mode)
    record_session_event(
        "trial_created",
        {
            "trial_filter_count": len(current_filters),
            "trial_filters": repr(current_filters),
            "trial_has_change": current_trial_has_change,
            "randomization_mode": selected_randomization_mode.get(),
        },
    )
    update_identification_answer_rows()
    reset_pending_detection_answer()
    set_identification_submit_enabled(False)
    if automobile_environment_is_active():
        set_feedback("New trial created with automobile simulation. Listen before answering.", MUTED_TEXT_COLOR)
    else:
        set_feedback("New trial created. Listen before answering.", MUTED_TEXT_COLOR)

def play_sample_a():
    """Play whichever file corresponds to Sample A for this trial."""
    reference_preview_file = prepare_selected_source_file()
    if not reference_preview_file:
        return

    if automobile_environment_is_active() and os.path.exists(modified_file):
        if not (os.path.exists(trial_reference_file) and os.path.exists(trial_modified_file)):
            ensure_conditioned_trial_files(reference_preview_file, current_trial_id)

    if automobile_environment_is_active() and os.path.exists(trial_reference_file) and os.path.exists(trial_modified_file):
        conditioned_reference = trial_reference_file
        conditioned_modified = trial_modified_file
    else:
        conditioned_reference = reference_preview_file
        conditioned_modified = modified_file

    if modified_sample == "A":
        filename = conditioned_modified
    else:
        filename = conditioned_reference

    play_audio_file(filename)


def play_sample_b():
    """Play whichever file corresponds to Sample B for this trial."""
    reference_preview_file = prepare_selected_source_file()
    if not reference_preview_file:
        return

    if automobile_environment_is_active() and os.path.exists(modified_file):
        if not (os.path.exists(trial_reference_file) and os.path.exists(trial_modified_file)):
            ensure_conditioned_trial_files(reference_preview_file, current_trial_id)

    if automobile_environment_is_active() and os.path.exists(trial_reference_file) and os.path.exists(trial_modified_file):
        conditioned_reference = trial_reference_file
        conditioned_modified = trial_modified_file
    else:
        conditioned_reference = reference_preview_file
        conditioned_modified = modified_file

    if modified_sample == "B":
        filename = conditioned_modified
    else:
        filename = conditioned_reference

    play_audio_file(filename)


# =========================
# GUI Data Binding Helpers
# =========================
def refresh_option_menu(option_menu, variable, options):
    """Replace an OptionMenu's entries while preserving the backing variable."""
    option_menu["menu"].delete(0, "end")
    for option in options:
        option_menu["menu"].add_command(
            label=str(option),
            command=lambda value=option: variable.set(value)
        )


def sync_constraint_control_states(*_):
    """Gray out constraint controls when they are not actively shaping trials."""
    range_enabled = lock_range.get()
    gain_direction = selected_gain_direction.get()
    cut_count_enabled = gain_direction != "Boost Only"
    boost_count_enabled = gain_direction != "Cut Only"
    cut_side_enabled = cut_count_enabled and selected_cut_count.get() > 0
    boost_side_enabled = boost_count_enabled and selected_boost_count.get() > 0
    cut_exact_enabled = cut_side_enabled
    boost_exact_enabled = boost_side_enabled

    range_state = "normal" if range_enabled else "disabled"
    cut_range_state = "normal" if cut_side_enabled else "disabled"
    boost_range_state = "normal" if boost_side_enabled else "disabled"
    cut_exact_state = "normal" if cut_exact_enabled else "disabled"
    boost_exact_state = "normal" if boost_exact_enabled else "disabled"

    # Frequency-range controls only matter when range locking is enabled.
    set_option_menu_state(range_min_menu, range_state)
    set_option_menu_state(range_max_menu, range_state)
    set_label_state(range_label, range_enabled)
    set_label_state(range_start_label, range_enabled)
    set_label_state(range_end_label, range_enabled)

    # Gain-pool controls only matter when exact gain is not locked.
    set_option_menu_state(gain_direction_menu, "normal")
    set_option_menu_state(cut_count_menu, "normal" if cut_count_enabled else "disabled")
    set_option_menu_state(boost_count_menu, "normal" if boost_count_enabled else "disabled")
    set_option_menu_state(cut_min_menu, cut_range_state)
    set_option_menu_state(cut_max_menu, cut_range_state)
    set_option_menu_state(boost_min_menu, boost_range_state)
    set_option_menu_state(boost_max_menu, boost_range_state)
    set_label_state(gain_direction_label, True)
    set_label_state(cut_count_label, cut_count_enabled)
    set_label_state(boost_count_label, boost_count_enabled)
    set_label_state(cut_range_label, cut_side_enabled)
    set_label_state(cut_start_label, cut_side_enabled)
    set_label_state(cut_end_label, cut_side_enabled)
    set_option_menu_state(exact_cut_menu, cut_exact_state)
    exact_cut_lock.configure(state=cut_exact_state)
    set_label_state(exact_cut_label, cut_exact_enabled)
    set_label_state(boost_range_label, boost_side_enabled)
    set_label_state(boost_start_label, boost_side_enabled)
    set_label_state(boost_end_label, boost_side_enabled)
    set_option_menu_state(exact_boost_menu, boost_exact_state)
    exact_boost_lock.configure(state=boost_exact_state)
    set_label_state(exact_boost_label, boost_exact_enabled)


def update_frequency_menu(*_):
    """Keep frequency dropdowns aligned with the currently selected band mode."""
    frequency_options = get_frequency_options(selected_band_mode.get())

    refresh_option_menu(frequency_menu, selected_frequency, frequency_options)
    refresh_option_menu(range_min_menu, selected_range_min, frequency_options)
    refresh_option_menu(range_max_menu, selected_range_max, frequency_options)

    if selected_frequency.get() not in frequency_options:
        selected_frequency.set(frequency_options[0])

    if selected_range_min.get() not in frequency_options:
        selected_range_min.set(frequency_options[0])

    if selected_range_max.get() not in frequency_options:
        selected_range_max.set(frequency_options[-1])

    update_identification_answer_rows()
    sync_constraint_control_states()
    update_status_label()


def normalize_range_variables(start_variable, end_variable):
    """Ensure start/end values stay in ascending order for cleaner status/UI."""
    start_value = start_variable.get()
    end_value = end_variable.get()

    if start_value > end_value:
        start_variable.set(end_value)
        end_variable.set(start_value)


def update_gain_ranges(*_):
    """Keep cut and boost range selectors ordered and reflected in status."""
    normalize_range_variables(selected_cut_min, selected_cut_max)
    normalize_range_variables(selected_boost_min, selected_boost_max)
    sync_constraint_control_states()
    update_status_label()


def update_filter_count_controls(*_):
    """Keep boost/cut count selectors within a three-filter total budget."""
    gain_direction = selected_gain_direction.get()

    if gain_direction == "Boost Only":
        if selected_cut_count.get() != 0:
            selected_cut_count.set(0)
            return
        if selected_boost_count.get() == 0:
            selected_boost_count.set(1)
            return

    if gain_direction == "Cut Only":
        if selected_boost_count.get() != 0:
            selected_boost_count.set(0)
            return
        if selected_cut_count.get() == 0:
            selected_cut_count.set(1)
            return

    cut_count = selected_cut_count.get()
    boost_count = selected_boost_count.get()

    if cut_count == 0 and boost_count == 0:
        selected_boost_count.set(1)
        return

    max_cut_count = 3 - boost_count
    max_boost_count = 3 - cut_count

    cut_options = list(range(0, max_cut_count + 1))
    boost_options = list(range(0, max_boost_count + 1))

    refresh_option_menu(cut_count_menu, selected_cut_count, cut_options)
    refresh_option_menu(boost_count_menu, selected_boost_count, boost_options)

    if selected_cut_count.get() not in cut_options:
        selected_cut_count.set(cut_options[-1])
        return

    if selected_boost_count.get() not in boost_options:
        selected_boost_count.set(boost_options[-1])
        return

    update_identification_answer_rows()
    sync_constraint_control_states()
    update_status_label()


def sync_automobile_control_states(*_):
    """Enable profile controls only when automobile monitoring is active."""
    enabled = selected_automobile_monitoring.get() == "On"
    state = "normal" if enabled else "disabled"

    set_option_menu_state(automobile_cabin_menu, state)
    set_option_menu_state(automobile_ac_menu, state)
    set_option_menu_state(automobile_loudness_menu, state)
    set_label_state(automobile_cabin_label, enabled)
    set_label_state(automobile_ac_label, enabled)
    set_label_state(automobile_loudness_label, enabled)


def open_settings_window():
    """Open the dedicated settings window."""
    settings_window.deiconify()
    settings_window.lift()
    settings_window.focus_force()


def save_and_close_settings_window():
    """Keep current selections and hide the settings window."""
    settings_window.withdraw()
    set_feedback("Settings saved and window closed.", MUTED_TEXT_COLOR)

# =========================
# GUI Setup
# =========================
# Tk state variables hold GUI selections and lock toggles.
# Practice ranges are separate from exact frequency/gain locks so users can
# constrain randomized drills without pinning one exact answer value.
root = create_root_window("Critical Listening Study", "1180x900")
root.protocol("WM_DELETE_WINDOW", on_app_close)

main_canvas = tk.Canvas(root, bg=root.cget("bg"), highlightthickness=0)
main_scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
main_canvas.configure(yscrollcommand=main_scrollbar.set)

main_scrollbar.pack(side="right", fill="y")
main_canvas.pack(side="left", fill="both", expand=True)

content_frame = tk.Frame(main_canvas, bg=root.cget("bg"))
canvas_window = main_canvas.create_window((0, 0), window=content_frame, anchor="nw")


def update_scroll_region(event):
    """Keep the scroll region aligned to the content size."""
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))


def resize_canvas_window(event):
    """Stretch the embedded content frame to the canvas width."""
    main_canvas.itemconfigure(canvas_window, width=event.width)


def scroll_with_mousewheel(event):
    """Enable mouse-wheel scrolling for the full settings panel."""
    main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


content_frame.bind("<Configure>", update_scroll_region)
main_canvas.bind("<Configure>", resize_canvas_window)
main_canvas.bind_all("<MouseWheel>", scroll_with_mousewheel)

settings_window = tk.Toplevel(root)
settings_window.title("Trial Settings")
settings_window.geometry("920x820")
settings_window.configure(bg=root.cget("bg"))
settings_window.withdraw()
settings_window.transient(root)
settings_window.protocol("WM_DELETE_WINDOW", save_and_close_settings_window)

settings_window_actions = tk.Frame(settings_window, bg=settings_window.cget("bg"))
settings_window_actions.pack(side="top", fill="x", padx=20, pady=(12, 0))

settings_window_close_button = tk.Button(
    settings_window_actions,
    text="Save And Close",
    command=save_and_close_settings_window,
)
settings_window_close_button.pack(side="right")

settings_canvas = tk.Canvas(settings_window, bg=settings_window.cget("bg"), highlightthickness=0)
settings_scrollbar = tk.Scrollbar(settings_window, orient="vertical", command=settings_canvas.yview)
settings_canvas.configure(yscrollcommand=settings_scrollbar.set)

settings_scrollbar.pack(side="right", fill="y")
settings_canvas.pack(side="left", fill="both", expand=True)

settings_window_content = tk.Frame(settings_canvas, bg=settings_window.cget("bg"))
settings_canvas_window = settings_canvas.create_window((0, 0), window=settings_window_content, anchor="nw")


def update_settings_scroll_region(event):
    """Keep the settings scroll region aligned to content height."""
    settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))


def resize_settings_canvas_window(event):
    """Stretch the settings content frame to the current canvas width."""
    settings_canvas.itemconfigure(settings_canvas_window, width=event.width)


settings_window_content.bind("<Configure>", update_settings_scroll_region)
settings_canvas.bind("<Configure>", resize_settings_canvas_window)

settings_notebook = ttk.Notebook(settings_window_content)
settings_notebook.pack(anchor="w", fill="both", expand=True, padx=20, pady=(6, 0))

trial_settings_tab = tk.Frame(settings_notebook, bg=settings_window.cget("bg"))
session_settings_tab = tk.Frame(settings_notebook, bg=settings_window.cget("bg"))
waveform_settings_tab = tk.Frame(settings_notebook, bg=settings_window.cget("bg"))
boost_cut_settings_tab = tk.Frame(settings_notebook, bg=settings_window.cget("bg"))
automobile_settings_tab = tk.Frame(settings_notebook, bg=settings_window.cget("bg"))

settings_notebook.add(trial_settings_tab, text="Trial Settings")
settings_notebook.add(session_settings_tab, text="Session Tracking")
settings_notebook.add(waveform_settings_tab, text="Waveform Selector")
settings_notebook.add(boost_cut_settings_tab, text="Boost / Cut")
settings_notebook.add(automobile_settings_tab, text="Automobile")

selected_gain = tk.IntVar(value=6)
selected_band_mode = tk.StringVar(value=BAND_MODES[0])
selected_range_min = tk.IntVar(value=get_frequency_options(BAND_MODES[0])[0])
selected_range_max = tk.IntVar(value=get_frequency_options(BAND_MODES[0])[-1])
selected_gain_direction = tk.StringVar(value=GAIN_DIRECTION_OPTIONS[0])
selected_cut_count = tk.IntVar(value=0)
selected_boost_count = tk.IntVar(value=1)
selected_cut_min = tk.IntVar(value=CUT_GAIN_OPTIONS[0])
selected_cut_max = tk.IntVar(value=CUT_GAIN_OPTIONS[-1])
selected_exact_cut = tk.IntVar(value=CUT_GAIN_OPTIONS[0])
selected_boost_min = tk.IntVar(value=BOOST_GAIN_OPTIONS[0])
selected_boost_max = tk.IntVar(value=BOOST_GAIN_OPTIONS[-1])
selected_exact_boost = tk.IntVar(value=BOOST_GAIN_OPTIONS[0])
selected_frequency = tk.IntVar(value=1000)
selected_q = tk.DoubleVar(value=1.0)
selected_randomization_mode = tk.StringVar(value=RANDOMIZATION_MODES[0])
selected_test_mode = tk.StringVar(value=TEST_MODE_OPTIONS[0])
selected_no_change_rate = tk.StringVar(value="Random")
selected_identification_target = tk.StringVar(value=IDENTIFICATION_TARGET_OPTIONS[0])
selected_section_length = tk.IntVar(value=8)
selected_automobile_monitoring = tk.StringVar(value=AUTOMOBILE_MONITOR_OPTIONS[0])
selected_automobile_cabin = tk.StringVar(value=AUTOMOBILE_CABIN_OPTIONS[0])
selected_automobile_ac = tk.StringVar(value=AUTOMOBILE_AC_OPTIONS[0])
selected_automobile_loudness = tk.StringVar(value=AUTOMOBILE_LOUDNESS_OPTIONS[0])
selected_automobile_preset = tk.StringVar(value="City Commute")
identification_answer_vars = [
    tk.DoubleVar(value=get_frequency_options(BAND_MODES[0])[0])
    for _ in range(MAX_FILTERS_PER_TRIAL)
]

lock_range = tk.BooleanVar(value=True)
lock_gain = tk.BooleanVar(value=False)
lock_exact_cut = tk.BooleanVar(value=False)
lock_exact_boost = tk.BooleanVar(value=False)
lock_band_mode = tk.BooleanVar(value=False)
lock_frequency = tk.BooleanVar(value=False)
lock_q = tk.BooleanVar(value=False)

# =========================
# Reference / Trial Playback Area
# =========================
# This area covers reference playback, trial playback, and trial settings.
title_label = create_section_label(
    content_frame,
    text="Critical Listening Study",
    font=("Arial", 20),
    pady=(30, 10),
)

dashboard_frame = tk.Frame(content_frame, bg=content_frame.cget("bg"))
dashboard_frame.pack(anchor="w", fill="x", padx=20, pady=(0, 10))

left_panel = tk.Frame(dashboard_frame, bg=content_frame.cget("bg"))
left_panel.pack(side="left", fill="both", expand=True, anchor="n")

reference_label = create_section_label(left_panel, text="Reference Audio", pady=(15, 1))

source_button_frame, (choose_file_button, play_reference_button, play_selected_section_button, stop_button) = create_button_row(
    left_panel,
    [
        ("Choose Audio File", choose_reference_file, (0, 5)),
        ("Play Source", play_reference, 5),
        ("Play Selected Section", play_selected_section, 5),
        ("Stop", stop_audio, 5),
    ],
    pady=(0, 5),
)

selected_file_label = tk.Label(
    left_panel,
    text="Selected File: None",
    fg=TEXT_COLOR,
    bg=left_panel.cget("bg")
)
selected_file_label.pack(
    anchor="w",
    padx=30,
    pady=(0, 8)
)

waveform_tab_section = tk.Frame(waveform_settings_tab, bg=waveform_settings_tab.cget("bg"))
waveform_tab_section.pack(anchor="w", fill="x", padx=20, pady=(18, 0))

waveform_tab_note = tk.Label(
    waveform_tab_section,
    text="Choose the source-file section used for trial rendering and practice examples.",
    fg=MUTED_TEXT_COLOR,
    bg=waveform_tab_section.cget("bg"),
    justify="left",
    wraplength=820,
)
waveform_tab_note.pack(anchor="w", padx=30, pady=(0, 8))

waveform_section_label = create_section_label(
    waveform_tab_section,
    text="Waveform Section Picker",
    font=("Arial", 14),
    pady=(0, 4),
)

waveform_helper_label = tk.Label(
    waveform_tab_section,
    text="Pick the section used for Source/Trials. Click waveform to set start and end, or auto-pick a loud section.",
    fg=MUTED_TEXT_COLOR,
    bg=waveform_tab_section.cget("bg"),
    justify="left",
    wraplength=820,
)
waveform_helper_label.pack(anchor="w", padx=30, pady=(0, 6))

waveform_canvas = tk.Canvas(
    waveform_tab_section,
    width=820,
    height=190,
    bg="#f7f7f7",
    highlightthickness=1,
    highlightbackground="#d0d0d0",
)
waveform_canvas.pack(anchor="w", padx=30, pady=(0, 6))
waveform_canvas.bind("<Button-1>", on_waveform_click)

waveform_selection_label = tk.Label(
    waveform_tab_section,
    text="No waveform loaded.",
    fg=MUTED_TEXT_COLOR,
    bg=waveform_tab_section.cget("bg"),
    justify="left",
    wraplength=820,
)
waveform_selection_label.pack(anchor="w", padx=30, pady=(0, 6))

waveform_section_row, waveform_section_row_label, waveform_section_menu = create_labeled_option_row(
    waveform_tab_section,
    label_text="Auto-Select Length (sec):",
    variable=selected_section_length,
    options=SECTION_LENGTH_OPTIONS,
    pady=(0, 6),
)

waveform_action_frame, waveform_action_buttons = create_button_row(
    waveform_tab_section,
    [
        ("Auto-Pick Loud Section", select_dense_section, (0, 5)),
        ("Use Full File", clear_section_selection, 5),
    ],
    pady=(0, 10),
)
auto_pick_section_button, use_full_file_button = waveform_action_buttons

trial_label = create_section_label(left_panel, text="Trial Audio", pady=(20, 1))

trial_button_frame, (sample_a_button, sample_b_button) = create_button_row(
    left_panel,
    [
        ("Play Sample A", play_sample_a, (0, 5)),
        ("Play Sample B", play_sample_b, 5),
    ],
    pady=(0, 5),
)

# Trial creation should stay near playback and response controls so it remains
# visible regardless of how tall the settings section becomes.
new_trial_button = tk.Button(
    left_panel,
    text="Generate New Trial",
    command=create_trial
)
new_trial_button.pack(
    anchor="w",
    padx=30,
    pady=(6, 2)
)

new_trial_help_label = tk.Label(
    left_panel,
    text=(
        "Creates one fresh trial using the current settings. In Mode 1, a no-change sample "
        "is used when the mix lands on a no-change outcome, or a random mix is used when Random is selected."
    ),
    fg=MUTED_TEXT_COLOR,
    bg=left_panel.cget("bg"),
    justify="left",
    wraplength=760,
)
new_trial_help_label.pack(anchor="w", padx=30, pady=(0, 10))

settings_button_row, (open_settings_button,) = create_button_row(
    left_panel,
    [
        ("Open Settings", open_settings_window, (0, 5)),
    ],
    pady=(0, 10),
)

# Keep the listener response controls near the trial playback buttons so users
# do not need to scroll visually past every settings block to answer.
response_section = tk.Frame(left_panel, bg=left_panel.cget("bg"))
response_section.pack(anchor="w", fill="x")

response_mode_row, response_mode_label, response_mode_menu = create_labeled_option_row(
    response_section,
    label_text="Test Mode:",
    variable=selected_test_mode,
    options=TEST_MODE_OPTIONS,
    pady=(12, 6),
)

mode1_options_label = create_section_label(
    response_section,
    text="Mode 1 Options",
    font=("Arial", 12),
    pady=(8, 2),
)

no_change_rate_row, no_change_rate_label, no_change_rate_menu = create_labeled_option_row(
    response_section,
    label_text="Change/No-Change Mix:",
    variable=selected_no_change_rate,
    options=NO_CHANGE_RATE_OPTIONS,
)

no_change_rate_help_label = tk.Label(
    response_section,
    text="Choose a fixed percentage for no-change trials, or leave Random selected for an unpredictable mix each time.",
    fg=MUTED_TEXT_COLOR,
    bg=response_section.cget("bg"),
    justify="left",
    wraplength=760,
)
no_change_rate_help_label.pack(anchor="w", padx=30, pady=(0, 8))

mode2_options_label = create_section_label(
    response_section,
    text="Mode 2 Options",
    font=("Arial", 12),
    pady=(8, 2),
)

mode2_options_hint_label = tk.Label(
    response_section,
    text="Set Identify target in Open Settings > Trial Settings.",
    fg=MUTED_TEXT_COLOR,
    bg=response_section.cget("bg"),
    justify="left",
    wraplength=760,
)
mode2_options_hint_label.pack(anchor="w", padx=30, pady=(0, 6))

# Mode 1 asks for simple change detection. Mode 2 switches to specific setting
# identification using the target and value controls below.
answer_label = create_section_label(
    response_section,
    text="Do Sample A and Sample B sound different?",
    pady=(16, 1),
)

yes_no_button_frame, (yes_button, no_button) = create_button_row(
    response_section,
    [
        ("Yes", lambda: select_detection_answer(True), (0, 5)),
        ("No", lambda: select_detection_answer(False), 5),
    ],
    pady=(0, 6),
)

mode1_selected_answer_label = tk.Label(
    response_section,
    text="Selected: none",
    fg=MUTED_TEXT_COLOR,
    bg=response_section.cget("bg")
)

submit_detection_button = tk.Button(
    response_section,
    text="Submit Answer",
    command=submit_detection_answer,
    state="disabled",
)

identification_prompt_label = tk.Label(
    response_section,
    text="Answer Value:",
    fg=TEXT_COLOR,
    bg=response_section.cget("bg")
)

identification_answer_rows = []
identification_value_menus = []
identification_answer_labels = []
for index, answer_var in enumerate(identification_answer_vars, start=1):
    answer_row, answer_value_label, answer_value_menu = create_labeled_option_row(
        response_section,
        label_text=f"Answer {index}:",
        variable=answer_var,
        options=get_identification_value_options(),
        pady=(0, 6),
    )
    identification_answer_rows.append(answer_row)
    identification_answer_labels.append(answer_value_label)
    identification_value_menus.append(answer_value_menu)
    answer_row.pack_forget()

check_answers_button = tk.Button(
    response_section,
    text="Check Answers",
    command=check_identification_response,
    state="disabled",
)

practice_tools_label = create_section_label(
    response_section,
    text="Reference Builder And Match Checker",
    pady=(8, 4),
)

practice_tools_note = tk.Label(
    response_section,
    text=(
        "Reference Builder: creates a study example from the settings window. "
        "Match Checker: creates what your current mode-2 guesses would sound like."
    ),
    fg=MUTED_TEXT_COLOR,
    bg=response_section.cget("bg")
)
practice_tools_note.pack(anchor="w", padx=30, pady=(0, 6))

practice_tools_frame, practice_tool_buttons = create_button_row(
    response_section,
    [
        ("Build Reference Example", render_memorization_audio, (0, 5)),
        ("Play Reference Example", play_memorization_audio, 5),
        ("Build Guess Example", render_match_audio, 5),
        ("Play Guess Example", play_match_audio, 5),
    ],
    pady=(0, 8),
)

feedback_label = tk.Label(
    response_section,
    text="No answer checked yet",
    fg=MUTED_TEXT_COLOR,
    bg=response_section.cget("bg")
)
feedback_label.pack(anchor="w", padx=30, pady=(0, 8))

score_label = tk.Label(
    response_section,
    text="Current Score: 0/0 (0%)",
    fg=TEXT_COLOR,
    bg=response_section.cget("bg")
)
score_label.pack(anchor="w", padx=30, pady=(0, 10))

settings_section = tk.Frame(trial_settings_tab, bg=trial_settings_tab.cget("bg"))
settings_section.pack(anchor="w", fill="x", padx=20, pady=(6, 0))

trial_tab_note = tk.Label(
    settings_section,
    text="Configure randomization, frequency band/range, and Q behavior for upcoming trials.",
    fg=MUTED_TEXT_COLOR,
    bg=settings_section.cget("bg"),
    justify="left",
    wraplength=840,
)
trial_tab_note.pack(anchor="w", padx=30, pady=(6, 0))

settings_header = tk.Frame(settings_section, bg=settings_section.cget("bg"))
settings_header.pack(anchor="w", fill="x")

settings_label = create_section_label(settings_header, text="Trial Settings", pady=(18, 5))

settings_content = tk.Frame(settings_section, bg=settings_section.cget("bg"))
settings_content.pack(anchor="w", fill="x")

settings_columns = tk.Frame(settings_content, bg=settings_content.cget("bg"))
settings_columns.pack(anchor="w", fill="x")

settings_left_column = tk.Frame(settings_columns, bg=settings_content.cget("bg"))
settings_left_column.pack(side="left", fill="both", expand=True, padx=(0, 18), anchor="n")

boost_cut_section = tk.Frame(boost_cut_settings_tab, bg=boost_cut_settings_tab.cget("bg"))
boost_cut_section.pack(anchor="w", fill="x", padx=20, pady=(18, 0))

boost_cut_tab_note = tk.Label(
    boost_cut_section,
    text="Set gain direction, cut/boost counts, and exact or ranged gain constraints.",
    fg=MUTED_TEXT_COLOR,
    bg=boost_cut_section.cget("bg"),
    justify="left",
    wraplength=840,
)
boost_cut_tab_note.pack(anchor="w", padx=30, pady=(0, 8))

boost_cut_label = create_section_label(
    boost_cut_section,
    text="Boost And Cut Controls",
    pady=(0, 6),
)

automobile_section = tk.Frame(automobile_settings_tab, bg=automobile_settings_tab.cget("bg"))
automobile_section.pack(anchor="w", fill="x", padx=20, pady=(18, 0))

automobile_tab_note = tk.Label(
    automobile_section,
    text=(
        "Emulate in-car listening by combining loudness presets with cabin and AC noise. "
        "When enabled, both trial samples use the same noise seed for fair A/B comparison."
    ),
    fg=MUTED_TEXT_COLOR,
    bg=automobile_section.cget("bg"),
    justify="left",
    wraplength=840,
)
automobile_tab_note.pack(anchor="w", padx=30, pady=(0, 8))

automobile_label = create_section_label(
    automobile_section,
    text="Automobile Listening Simulation",
    pady=(0, 6),
)

automobile_monitoring_row, automobile_monitoring_label, automobile_monitoring_menu = create_labeled_option_row(
    automobile_section,
    label_text="Automobile Simulation:",
    variable=selected_automobile_monitoring,
    options=AUTOMOBILE_MONITOR_OPTIONS,
)

automobile_cabin_row, automobile_cabin_label, automobile_cabin_menu = create_labeled_option_row(
    automobile_section,
    label_text="Cabin Condition:",
    variable=selected_automobile_cabin,
    options=AUTOMOBILE_CABIN_OPTIONS,
)

automobile_ac_row, automobile_ac_label, automobile_ac_menu = create_labeled_option_row(
    automobile_section,
    label_text="Air Conditioning:",
    variable=selected_automobile_ac,
    options=AUTOMOBILE_AC_OPTIONS,
)

automobile_loudness_row, automobile_loudness_label, automobile_loudness_menu = create_labeled_option_row(
    automobile_section,
    label_text="Loudness Preset:",
    variable=selected_automobile_loudness,
    options=AUTOMOBILE_LOUDNESS_OPTIONS,
)

automobile_quick_preset_label = create_section_label(
    automobile_section,
    text="One-Click Preset",
    font=("Arial", 12),
    pady=(8, 2),
)

automobile_preset_row, automobile_preset_label, automobile_preset_menu = create_labeled_option_row(
    automobile_section,
    label_text="Preset:",
    variable=selected_automobile_preset,
    options=AUTOMOBILE_PRESET_OPTIONS,
)

automobile_preset_button_frame, (automobile_apply_preset_button,) = create_button_row(
    automobile_section,
    [("Apply Preset", apply_automobile_preset, (0, 5))],
    pady=(0, 10),
)

session_section = tk.Frame(session_settings_tab, bg=session_settings_tab.cget("bg"))
session_section.pack(anchor="w", fill="x", padx=20, pady=(18, 0))

session_tab_note = tk.Label(
    session_section,
    text="Review score history, reset stats, start fresh sessions, and export results.",
    fg=MUTED_TEXT_COLOR,
    bg=session_section.cget("bg"),
    justify="left",
    wraplength=840,
)
session_tab_note.pack(anchor="w", padx=30, pady=(0, 8))

session_tools_label = create_section_label(
    session_section,
    text="Session Tracking",
    pady=(18, 4),
)

session_tools_frame, session_tool_buttons = create_button_row(
    session_section,
    [
        ("Start New Session", start_new_session, (0, 5)),
        ("Reset Session Stats", reset_session_stats, (0, 5)),
        ("Export Session Results", export_session_results, 5),
    ],
    pady=(0, 6),
)

session_stats_label = tk.Label(
    session_section,
    text="",
    justify="left",
    anchor="w",
    fg=TEXT_COLOR,
    bg=session_section.cget("bg")
)
session_stats_label.pack(anchor="w", padx=30, pady=(0, 10))

# Randomization mode decides whether unlocked controls are randomized or held.

randomization_mode_row, randomization_mode_label, randomization_mode_menu = create_labeled_option_row(
    settings_left_column,
    label_text="Randomization Mode:",
    variable=selected_randomization_mode,
    options=RANDOMIZATION_MODES,
    pady=(0, 10),
)

identification_target_row, identification_target_label, identification_target_menu = create_labeled_option_row(
    settings_left_column,
    label_text="Mode 2 Identify:",
    variable=selected_identification_target,
    options=IDENTIFICATION_TARGET_OPTIONS,
)

# Band mode chooses the master frequency list that all other frequency controls use.
band_row, band_label, band_menu, band_lock = create_labeled_option_with_lock_row(
    settings_left_column,
    label_text="Frequency Bands:",
    variable=selected_band_mode,
    options=BAND_MODES,
    lock_variable=lock_band_mode,
)

# When Range lock is on, randomized trials stay inside this frequency span.
range_row, range_label, range_start_label, range_min_menu, range_end_label, range_max_menu, range_lock = create_range_option_row(
    settings_left_column,
    label_text="Practice Frequency Range (Hz):",
    start_variable=selected_range_min,
    start_options=get_frequency_options(selected_band_mode.get()),
    end_variable=selected_range_max,
    end_options=get_frequency_options(selected_band_mode.get()),
    lock_variable=lock_range,
)

frequency_row, frequency_label, frequency_menu, frequency_lock = create_labeled_option_with_lock_row(
    settings_left_column,
    label_text="Frequency (Hz):",
    variable=selected_frequency,
    options=get_frequency_options(selected_band_mode.get()),
    lock_variable=lock_frequency,
)

q_row, q_label, q_menu, q_lock = create_labeled_option_with_lock_row(
    settings_left_column,
    label_text="Q Factor:",
    variable=selected_q,
    options=Q_OPTIONS,
    lock_variable=lock_q,
    pady=(0, 10),
)

# Exact gain lock pins one dB value. The gain range controls below constrain
# the pool used when gain is allowed to randomize.
gain_row, gain_label, gain_menu, gain_lock = create_labeled_option_with_lock_row(
    boost_cut_section,
    label_text="Gain:",
    variable=selected_gain,
    options=GAIN_OPTIONS,
    lock_variable=lock_gain,
)

gain_direction_row, gain_direction_label, gain_direction_menu = create_labeled_option_row(
    boost_cut_section,
    label_text="Gain Direction:",
    variable=selected_gain_direction,
    options=GAIN_DIRECTION_OPTIONS,
)

# These counts control how many EQ changes can appear in one trial. The total
# is capped at three so users can do all boosts, all cuts, or mixed patterns.
cut_count_row, cut_count_label, cut_count_menu = create_labeled_option_row(
    boost_cut_section,
    label_text="Cut Count:",
    variable=selected_cut_count,
    options=FILTER_COUNT_OPTIONS,
)

boost_count_row, boost_count_label, boost_count_menu = create_labeled_option_row(
    boost_cut_section,
    label_text="Boost Count:",
    variable=selected_boost_count,
    options=FILTER_COUNT_OPTIONS,
)

# Cut and boost ranges let users practice only negative or positive EQ moves,
# or combine both while still keeping exact-gain locking separate.
cut_range_row, cut_range_label, cut_start_label, cut_min_menu, cut_end_label, cut_max_menu, cut_range_lock = create_range_option_row(
    boost_cut_section,
    label_text="Cut Gain Range (dB):",
    start_variable=selected_cut_min,
    start_options=CUT_GAIN_OPTIONS,
    end_variable=selected_cut_max,
    end_options=CUT_GAIN_OPTIONS,
    pady=(0, 6),
)

# Exact cut lock pins one negative-gain amount while still leaving the broader
# generic gain lock and cut range controls available when needed.
exact_cut_row, exact_cut_label, exact_cut_menu, exact_cut_lock = create_labeled_option_with_lock_row(
    boost_cut_section,
    label_text="Exact Cut Amount (dB):",
    variable=selected_exact_cut,
    options=CUT_GAIN_OPTIONS,
    lock_variable=lock_exact_cut,
)

boost_range_row, boost_range_label, boost_start_label, boost_min_menu, boost_end_label, boost_max_menu, boost_range_lock = create_range_option_row(
    boost_cut_section,
    label_text="Boost Gain Range (dB):",
    start_variable=selected_boost_min,
    start_options=BOOST_GAIN_OPTIONS,
    end_variable=selected_boost_max,
    end_options=BOOST_GAIN_OPTIONS,
    pady=(0, 6),
)

# Exact boost lock pins one positive-gain amount while still leaving the broader
# generic gain lock and boost range controls available when needed.
exact_boost_row, exact_boost_label, exact_boost_menu, exact_boost_lock = create_labeled_option_with_lock_row(
    boost_cut_section,
    label_text="Exact Boost Amount (dB):",
    variable=selected_exact_boost,
    options=BOOST_GAIN_OPTIONS,
    lock_variable=lock_exact_boost,
)


selected_band_mode.trace_add("write", update_frequency_menu)
selected_test_mode.trace_add("write", update_response_mode)
selected_identification_target.trace_add("write", update_identification_value_menu)
selected_identification_target.trace_add("write", lambda *_: update_identification_answer_rows())
for answer_var in identification_answer_vars:
    answer_var.trace_add("write", on_identification_answer_changed)
selected_cut_count.trace_add("write", update_filter_count_controls)
selected_boost_count.trace_add("write", update_filter_count_controls)
selected_range_min.trace_add("write", lambda *_: normalize_range_variables(selected_range_min, selected_range_max))
selected_range_max.trace_add("write", lambda *_: normalize_range_variables(selected_range_min, selected_range_max))
selected_cut_min.trace_add("write", update_gain_ranges)
selected_cut_max.trace_add("write", update_gain_ranges)
selected_boost_min.trace_add("write", update_gain_ranges)
selected_boost_max.trace_add("write", update_gain_ranges)
lock_range.trace_add("write", sync_constraint_control_states)
lock_gain.trace_add("write", sync_constraint_control_states)
lock_exact_cut.trace_add("write", sync_constraint_control_states)
lock_exact_boost.trace_add("write", sync_constraint_control_states)
selected_gain_direction.trace_add("write", sync_constraint_control_states)
selected_gain_direction.trace_add("write", update_filter_count_controls)
selected_automobile_monitoring.trace_add("write", sync_automobile_control_states)
selected_automobile_monitoring.trace_add("write", invalidate_conditioned_trial_audio)
selected_automobile_cabin.trace_add("write", invalidate_conditioned_trial_audio)
selected_automobile_ac.trace_add("write", invalidate_conditioned_trial_audio)
selected_automobile_loudness.trace_add("write", invalidate_conditioned_trial_audio)
update_frequency_menu()
update_filter_count_controls()
sync_constraint_control_states()
sync_automobile_control_states()
update_response_mode()
set_feedback("No answer checked yet", MUTED_TEXT_COLOR)
update_session_stats_label()

randomization_note = tk.Label(
    settings_section,
    text="Randomize Unlocked respects each Lock checkbox. Disabled controls are currently not affecting trial generation. Use Save And Close when you are done.",
    fg=MUTED_TEXT_COLOR,
    bg=settings_section.cget("bg")
)
randomization_note.pack(
    anchor="w",
    padx=30,
    pady=(0, 10)
)

status_label = create_status_panel(left_panel, wraplength=500)

bind_live_update([
    selected_randomization_mode,
    selected_test_mode,
    selected_no_change_rate,
    selected_identification_target,
    selected_automobile_monitoring,
    selected_automobile_cabin,
    selected_automobile_ac,
    selected_automobile_loudness,
    selected_band_mode,
    selected_range_min,
    selected_range_max,
    selected_gain_direction,
    selected_cut_count,
    selected_boost_count,
    selected_cut_min,
    selected_cut_max,
    selected_exact_cut,
    selected_boost_min,
    selected_boost_max,
    selected_exact_boost,
    selected_frequency,
    selected_gain,
    selected_q,
    lock_band_mode,
    lock_range,
    lock_frequency,
    lock_gain,
    lock_exact_cut,
    lock_exact_boost,
    lock_q,
] + identification_answer_vars, update_status_label)

root.mainloop()