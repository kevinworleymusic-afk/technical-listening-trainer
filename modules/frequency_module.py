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

AUTOMOBILE_CABIN_OPTIONS = [
    "Off",
    "Parked Cabin",
    "City Streets",
    "Highway Cruise",
    "Windows Open",
]
AUTOMOBILE_AC_OPTIONS = ["Off", "Low", "Medium", "High"]
AUTOMOBILE_LOUDNESS_OPTIONS = ["Reference", "Comfort", "Commute", "Loud"]

OCTAVE_FREQUENCIES = [125, 250, 500, 1000, 2000, 4000, 8000, 16000]
THIRD_OCTAVE_FREQUENCIES = [
    125, 160, 200, 250, 315, 400, 500, 630, 800,
    1000, 1250, 1600, 2000, 2500, 3150,
    4000, 5000, 6300, 8000, 10000, 12500, 16000,
]


_CABIN_NOISE_RMS_BY_PROFILE = {
    "Off": 0.0,
    "Parked Cabin": 0.004,
    "City Streets": 0.012,
    "Highway Cruise": 0.02,
    "Windows Open": 0.035,
}

_CABIN_LOWPASS_HZ_BY_PROFILE = {
    "Off": 9000,
    "Parked Cabin": 6500,
    "City Streets": 5200,
    "Highway Cruise": 4200,
    "Windows Open": 3000,
}

_AC_NOISE_RMS_BY_LEVEL = {
    "Off": 0.0,
    "Low": 0.003,
    "Medium": 0.006,
    "High": 0.01,
}

_LOUDNESS_GAIN_DB_BY_MODE = {
    "Reference": 0.0,
    "Comfort": 2.0,
    "Commute": 5.0,
    "Loud": 8.0,
}


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


def _limit_signal_peak(audio, peak=0.98):
    """Keep output inside a stable peak target to avoid clipping."""
    maximum = float(np.max(np.abs(audio)))
    if maximum <= peak or maximum == 0.0:
        return audio
    return audio * (peak / maximum)


def _mix_weighted_noise(audio_shape, noise_components):
    """Build a weighted sum of white-noise components for mono/stereo signals."""
    if not noise_components:
        return np.zeros(audio_shape, dtype=np.float32)

    mixed = np.zeros(audio_shape, dtype=np.float32)
    for noise_component, weight in noise_components:
        mixed += noise_component.astype(np.float32) * float(weight)
    return mixed


def _generate_cabin_noise(sample_count, sample_rate, profile):
    """Generate low-frequency weighted road/cabin noise for one profile."""
    target_rms = _CABIN_NOISE_RMS_BY_PROFILE.get(profile, 0.0)
    if target_rms <= 0.0:
        return np.zeros(sample_count, dtype=np.float32)

    white = np.random.normal(0.0, 1.0, sample_count).astype(np.float32)
    lowpass_hz = _CABIN_LOWPASS_HZ_BY_PROFILE.get(profile, 5000)
    normalized_cutoff = max(0.01, min(0.95, lowpass_hz / (sample_rate / 2.0)))
    b, a = signal.butter(2, normalized_cutoff, btype="low")
    rumble = signal.lfilter(b, a, white)

    rms = float(np.sqrt(np.mean(rumble**2)))
    if rms > 0.0:
        rumble = rumble * (target_rms / rms)

    return rumble.astype(np.float32)


def _generate_ac_noise(sample_count, sample_rate, ac_level):
    """Generate band-limited fan/vent noise for AC simulation."""
    target_rms = _AC_NOISE_RMS_BY_LEVEL.get(ac_level, 0.0)
    if target_rms <= 0.0:
        return np.zeros(sample_count, dtype=np.float32)

    white = np.random.normal(0.0, 1.0, sample_count).astype(np.float32)
    highpass_hz = 600.0
    lowpass_hz = 8000.0
    hp_norm = max(0.001, min(0.95, highpass_hz / (sample_rate / 2.0)))
    lp_norm = max(0.01, min(0.95, lowpass_hz / (sample_rate / 2.0)))
    b_hp, a_hp = signal.butter(1, hp_norm, btype="high")
    b_lp, a_lp = signal.butter(1, lp_norm, btype="low")
    shaped = signal.lfilter(b_hp, a_hp, white)
    shaped = signal.lfilter(b_lp, a_lp, shaped)

    rms = float(np.sqrt(np.mean(shaped**2)))
    if rms > 0.0:
        shaped = shaped * (target_rms / rms)

    return shaped.astype(np.float32)


def apply_automobile_environment(audio, sample_rate, environment_settings=None, noise_seed=None):
    """Apply loudness and cabin/AC masking to emulate in-car listening."""
    if not environment_settings:
        return audio

    cabin_profile = environment_settings.get("cabin_profile", "Off")
    ac_level = environment_settings.get("ac_level", "Off")
    loudness_mode = environment_settings.get("loudness_mode", "Reference")

    if (
        cabin_profile == "Off"
        and ac_level == "Off"
        and loudness_mode == "Reference"
    ):
        return audio

    if noise_seed is not None:
        np.random.seed(int(noise_seed))

    processed = np.array(audio, dtype=np.float32, copy=True)
    gain_db = _LOUDNESS_GAIN_DB_BY_MODE.get(loudness_mode, 0.0)
    processed *= 10 ** (gain_db / 20.0)

    sample_count = processed.shape[0]
    cabin_noise = _generate_cabin_noise(sample_count, sample_rate, cabin_profile)
    ac_noise = _generate_ac_noise(sample_count, sample_rate, ac_level)

    if processed.ndim == 1:
        processed += cabin_noise + ac_noise
    else:
        channels = processed.shape[1]
        per_channel_noise = _mix_weighted_noise(
            processed.shape,
            [
                (np.repeat(cabin_noise[:, None], channels, axis=1), 1.0),
                (np.repeat(ac_noise[:, None], channels, axis=1), 1.0),
            ],
        )
        processed += per_channel_noise

    processed = _limit_signal_peak(processed, peak=0.98)
    return processed.astype(audio.dtype, copy=False)


def create_passthrough_audio(input_file, output_file, environment_settings=None, noise_seed=None):
    """Write an unchanged copy of the source audio for no-change trials."""
    audio, sample_rate = sf.read(input_file)
    rendered = apply_automobile_environment(
        audio,
        sample_rate,
        environment_settings=environment_settings,
        noise_seed=noise_seed,
    )
    sf.write(output_file, rendered, sample_rate)
    print("Created unchanged trial:", output_file)


def create_modified_audio(
    input_file,
    output_file,
    frequency_or_filters,
    gain_db=None,
    q=None,
    environment_settings=None,
    noise_seed=None,
):
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

    modified = apply_automobile_environment(
        modified,
        sample_rate,
        environment_settings=environment_settings,
        noise_seed=noise_seed,
    )

    sf.write(output_file, modified, sample_rate)

    difference = np.max(np.abs(modified - audio))
    print("Maximum sample difference:", difference)
    print("Created:", output_file)


def resolve_no_change_probability(no_change_probability):
    """Normalize no-change probability values for trial generation."""
    if no_change_probability is None:
        return None

    if isinstance(no_change_probability, str):
        normalized = no_change_probability.strip().lower()
        if normalized in {"random", "randomized", "randomly"}:
            return None
        if normalized.endswith("%"):
            normalized = normalized[:-1]
        return float(normalized) / 100.0

    return float(no_change_probability) / 100.0 if no_change_probability <= 1 else float(no_change_probability) / 100.0


def create_trial_audio(
    input_file,
    output_file,
    selected_values,
    lock_values,
    randomization_mode,
    allow_no_change=False,
    no_change_probability=0.5,
    environment_settings=None,
    noise_seed=None,
):
    """Create one frequency-module trial and render audio stimulus."""
    params = resolve_trial_parameters(selected_values, lock_values, randomization_mode)
    modified_sample = random.choice(SAMPLE_OPTIONS)
    probability = resolve_no_change_probability(no_change_probability)
    resolved_probability = probability if probability is not None else random.random()

    if allow_no_change and random.random() < resolved_probability:
        create_passthrough_audio(
            input_file,
            output_file,
            environment_settings=environment_settings,
            noise_seed=noise_seed,
        )
        params["modified_sample"] = modified_sample
        params["has_change"] = False
        params["filters"] = []
        return params

    create_modified_audio(
        input_file,
        output_file,
        params["filters"],
        environment_settings=environment_settings,
        noise_seed=noise_seed,
    )

    params["modified_sample"] = modified_sample
    params["has_change"] = True
    return params


def create_automobile_conditioned_audio(
    input_file,
    output_file,
    environment_settings=None,
    noise_seed=None,
):
    """Render a source file through the automobile environment settings only."""
    audio, sample_rate = sf.read(input_file)
    rendered = apply_automobile_environment(
        audio,
        sample_rate,
        environment_settings=environment_settings,
        noise_seed=noise_seed,
    )
    sf.write(output_file, rendered, sample_rate)
