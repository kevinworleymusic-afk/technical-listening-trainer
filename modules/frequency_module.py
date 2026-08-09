import random

import numpy as np
import soundfile as sf
from scipy import signal


# =========================
# Frequency Module Options
# =========================
CUT_GAIN_OPTIONS = list(range(-12, 0))
BOOST_GAIN_OPTIONS = list(range(1, 13))
GAIN_OPTIONS = CUT_GAIN_OPTIONS + [0] + BOOST_GAIN_OPTIONS
GAIN_DIRECTION_OPTIONS = ["Boost and Cut", "Boost Only", "Cut Only"]
FILTER_COUNT_OPTIONS = [0, 1, 2, 3]
Q_OPTIONS = [0.5, 1, 2, 4, 8]
BAND_MODES = ["1 Octave", "1/3 Octave"]
RANDOMIZATION_MODES = ["Randomize Unlocked", "Randomize All", "Use Selected Values"]
SAMPLE_OPTIONS = ["A", "B"]

OCTAVE_FREQUENCIES = [125, 250, 500, 1000, 2000, 4000, 8000, 16000]
THIRD_OCTAVE_FREQUENCIES = [
    125, 160, 200, 250, 315, 400, 500, 630, 800,
    1000, 1250, 1600, 2000, 2500, 3150,
    4000, 5000, 6300, 8000, 10000, 12500, 16000,
]


# =========================
# Frequency Trial Selection
# =========================
def get_frequency_options(band_mode):
    """Return center frequencies for the selected band spacing."""
    if band_mode == "1 Octave":
        return OCTAVE_FREQUENCIES
    return THIRD_OCTAVE_FREQUENCIES


def get_practice_frequency_options(band_mode, minimum_frequency=None, maximum_frequency=None):
    """Return the active practice pool constrained to the requested range."""
    frequency_options = get_frequency_options(band_mode)

    if minimum_frequency is None and maximum_frequency is None:
        return frequency_options

    lower_bound = minimum_frequency if minimum_frequency is not None else frequency_options[0]
    upper_bound = maximum_frequency if maximum_frequency is not None else frequency_options[-1]

    if lower_bound > upper_bound:
        lower_bound, upper_bound = upper_bound, lower_bound

    filtered_options = [
        frequency for frequency in frequency_options
        if lower_bound <= frequency <= upper_bound
    ]

    if filtered_options:
        return filtered_options

    return frequency_options


def _filter_range(options, minimum_value=None, maximum_value=None):
    """Return values inside a selected numeric range, regardless of bound order."""
    if minimum_value is None and maximum_value is None:
        return options

    lower_bound = minimum_value if minimum_value is not None else options[0]
    upper_bound = maximum_value if maximum_value is not None else options[-1]

    if lower_bound > upper_bound:
        lower_bound, upper_bound = upper_bound, lower_bound

    filtered_options = [option for option in options if lower_bound <= option <= upper_bound]
    if filtered_options:
        return filtered_options

    return options


def get_practice_gain_options(
    gain_direction,
    cut_minimum=None,
    cut_maximum=None,
    boost_minimum=None,
    boost_maximum=None,
    exact_cut=None,
    exact_boost=None,
    lock_exact_cut=False,
    lock_exact_boost=False,
):
    """Return the active gain pool using separate cut and boost ranges.

    These ranges only matter when exact gain is not locked in the GUI.
    """
    if lock_exact_cut and exact_cut in CUT_GAIN_OPTIONS:
        cut_options = [exact_cut]
    else:
        cut_options = _filter_range(CUT_GAIN_OPTIONS, cut_minimum, cut_maximum)

    if lock_exact_boost and exact_boost in BOOST_GAIN_OPTIONS:
        boost_options = [exact_boost]
    else:
        boost_options = _filter_range(BOOST_GAIN_OPTIONS, boost_minimum, boost_maximum)

    if gain_direction == "Cut Only":
        return cut_options
    if gain_direction == "Boost Only":
        return boost_options
    return cut_options + boost_options


def _should_randomize(randomization_mode, is_locked):
    """Apply shared mode/lock logic to one parameter group."""
    if randomization_mode == "Use Selected Values":
        return False
    if randomization_mode == "Randomize All":
        return True
    return not is_locked


def _select_filter_frequencies(frequency_pool, selected_frequency, randomize_frequency, filter_count):
    """Return one center frequency per filter, preferring unique values when random."""
    if filter_count <= 0:
        return []

    if not randomize_frequency:
        chosen_frequency = selected_frequency
        if chosen_frequency not in frequency_pool:
            chosen_frequency = frequency_pool[0]
        return [chosen_frequency] * filter_count

    if len(frequency_pool) >= filter_count:
        return random.sample(frequency_pool, filter_count)

    return [random.choice(frequency_pool) for _ in range(filter_count)]


def _select_filter_q_values(selected_q, randomize_q, filter_count):
    """Return one Q value per filter."""
    if filter_count <= 0:
        return []

    if not randomize_q:
        return [selected_q] * filter_count

    return [random.choice(Q_OPTIONS) for _ in range(filter_count)]


def _select_side_gains(filter_type, selected_values, lock_values, randomization_mode, filter_count):
    """Return gains for one side of the EQ change list."""
    if filter_count <= 0:
        return []

    if filter_type == "cut":
        side_pool = get_practice_gain_options(
            "Cut Only",
            selected_values.get("cut_min"),
            selected_values.get("cut_max"),
            selected_values.get("boost_min"),
            selected_values.get("boost_max"),
            selected_values.get("exact_cut"),
            selected_values.get("exact_boost"),
            lock_values.get("exact_cut", False),
            lock_values.get("exact_boost", False),
        )
        fallback_value = selected_values.get("exact_cut", CUT_GAIN_OPTIONS[0])
    else:
        side_pool = get_practice_gain_options(
            "Boost Only",
            selected_values.get("cut_min"),
            selected_values.get("cut_max"),
            selected_values.get("boost_min"),
            selected_values.get("boost_max"),
            selected_values.get("exact_cut"),
            selected_values.get("exact_boost"),
            lock_values.get("exact_cut", False),
            lock_values.get("exact_boost", False),
        )
        fallback_value = selected_values.get("exact_boost", BOOST_GAIN_OPTIONS[0])

    if not side_pool:
        side_pool = [fallback_value]

    if not _should_randomize(randomization_mode, lock_values["gain"]):
        selected_gain = selected_values.get("gain", fallback_value)
        if filter_type == "cut":
            resolved_gain = -abs(selected_gain) if selected_gain != 0 else fallback_value
            if resolved_gain not in CUT_GAIN_OPTIONS:
                resolved_gain = fallback_value
        else:
            resolved_gain = abs(selected_gain) if selected_gain != 0 else fallback_value
            if resolved_gain not in BOOST_GAIN_OPTIONS:
                resolved_gain = fallback_value
        return [resolved_gain] * filter_count

    return [random.choice(side_pool) for _ in range(filter_count)]


def resolve_trial_parameters(selected_values, lock_values, randomization_mode):
    """Resolve final band/frequency/gain/Q settings for one trial."""
    if _should_randomize(randomization_mode, lock_values["band_mode"]):
        band_mode = random.choice(BAND_MODES)
    else:
        band_mode = selected_values["band_mode"]

    # Range locking constrains randomized frequency practice to the chosen span.
    if lock_values.get("range", False):
        frequency_pool = get_practice_frequency_options(
            band_mode,
            selected_values.get("range_min"),
            selected_values.get("range_max"),
        )
    else:
        frequency_pool = get_frequency_options(band_mode)

    cut_count = max(0, min(3, int(selected_values.get("cut_count", 0))))
    boost_count = max(0, min(3, int(selected_values.get("boost_count", 1))))
    if cut_count + boost_count == 0:
        boost_count = 1
    if cut_count + boost_count > 3:
        overflow = cut_count + boost_count - 3
        if boost_count >= overflow:
            boost_count -= overflow
        else:
            cut_count = max(0, cut_count - (overflow - boost_count))
            boost_count = 0

    total_filters = cut_count + boost_count
    randomize_frequency = _should_randomize(randomization_mode, lock_values["frequency"])
    selected_frequency = selected_values.get("frequency")
    filter_frequencies = _select_filter_frequencies(
        frequency_pool,
        selected_frequency,
        randomize_frequency,
        total_filters,
    )

    randomize_q = _should_randomize(randomization_mode, lock_values["q"])
    filter_q_values = _select_filter_q_values(
        selected_values.get("q", Q_OPTIONS[0]),
        randomize_q,
        total_filters,
    )

    cut_gains = _select_side_gains(
        "cut",
        selected_values,
        lock_values,
        randomization_mode,
        cut_count,
    )
    boost_gains = _select_side_gains(
        "boost",
        selected_values,
        lock_values,
        randomization_mode,
        boost_count,
    )

    filter_definitions = (["cut"] * cut_count) + (["boost"] * boost_count)
    filters = []
    for index, filter_type in enumerate(filter_definitions):
        gains = cut_gains if filter_type == "cut" else boost_gains
        gain_index = index if filter_type == "cut" else index - cut_count
        filters.append(
            {
                "type": filter_type,
                "frequency": filter_frequencies[index],
                "gain": gains[gain_index],
                "q": filter_q_values[index],
            }
        )

    first_filter = filters[0]

    return {
        "band_mode": band_mode,
        "frequency": first_filter["frequency"],
        "gain": first_filter["gain"],
        "q": first_filter["q"],
        "cut_count": cut_count,
        "boost_count": boost_count,
        "filters": filters,
    }


# =========================
# Frequency DSP Processing
# =========================
def _design_peaking_filter(sample_rate, frequency, gain_db, q):
    """Return IIR coefficients for one peaking EQ filter."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * frequency / sample_rate
    alpha = np.sin(w0) / (2 * q)

    b0 = 1 + alpha * A
    b1 = -2 * np.cos(w0)
    b2 = 1 - alpha * A

    a0 = 1 + alpha / A
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha / A

    b = np.array([b0, b1, b2]) / a0
    a = np.array([a0, a1, a2]) / a0
    return b, a


def create_passthrough_audio(input_file, output_file):
    """Write an unchanged copy of the source audio for no-change trials."""
    audio, sample_rate = sf.read(input_file)
    sf.write(output_file, audio, sample_rate)
    print("Created unchanged trial:", output_file)


def create_modified_audio(input_file, output_file, frequency_or_filters, gain_db=None, q=None):
    """Apply one or more peaking EQ filters and write a modified audio file."""
    audio, sample_rate = sf.read(input_file)

    if isinstance(frequency_or_filters, list):
        filters = frequency_or_filters
    else:
        filters = [{"type": "single", "frequency": frequency_or_filters, "gain": gain_db, "q": q}]

    modified = audio
    for index, filter_settings in enumerate(filters, start=1):
        b, a = _design_peaking_filter(
            sample_rate,
            filter_settings["frequency"],
            filter_settings["gain"],
            filter_settings["q"],
        )

        w, h = signal.freqz(b, a, worN=4096, fs=sample_rate)
        peak_index = np.argmax(np.abs(h))
        peak_frequency = w[peak_index]
        peak_gain_db = 20 * np.log10(np.abs(h[peak_index]))

        print(
            f"Filter {index}: {filter_settings['type']} @ "
            f"{filter_settings['frequency']} Hz, {filter_settings['gain']} dB, Q={filter_settings['q']}"
        )
        print("Peak frequency:", peak_frequency)
        print("Peak gain dB:", peak_gain_db)

        modified = signal.lfilter(b, a, modified, axis=0)

    sf.write(output_file, modified, sample_rate)

    difference = np.max(np.abs(modified - audio))
    print("Maximum sample difference:", difference)
    print("Created:", output_file)


def create_trial_audio(
    input_file,
    output_file,
    selected_values,
    lock_values,
    randomization_mode,
    allow_no_change=False,
    no_change_probability=0.5,
):
    """Create one frequency-module trial and render audio stimulus."""
    params = resolve_trial_parameters(selected_values, lock_values, randomization_mode)
    modified_sample = random.choice(SAMPLE_OPTIONS)

    if allow_no_change and random.random() < no_change_probability:
        create_passthrough_audio(input_file, output_file)
        params["modified_sample"] = modified_sample
        params["has_change"] = False
        params["filters"] = []
        return params

    create_modified_audio(
        input_file,
        output_file,
        params["filters"],
    )

    params["modified_sample"] = modified_sample
    params["has_change"] = True
    return params
