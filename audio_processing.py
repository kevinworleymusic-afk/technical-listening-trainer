"""Compatibility facade for legacy imports.

Primary frequency-module logic now lives in `modules/frequency_module.py`.
Keep importing from this file if existing scripts depend on it.
"""

from modules.frequency_module import BAND_MODES
from modules.frequency_module import AUTOMOBILE_AC_OPTIONS
from modules.frequency_module import AUTOMOBILE_CABIN_OPTIONS
from modules.frequency_module import AUTOMOBILE_LOUDNESS_OPTIONS
from modules.frequency_module import BOOST_GAIN_OPTIONS
from modules.frequency_module import CUT_GAIN_OPTIONS
from modules.frequency_module import FILTER_COUNT_OPTIONS
from modules.frequency_module import GAIN_DIRECTION_OPTIONS
from modules.frequency_module import GAIN_OPTIONS
from modules.frequency_module import OCTAVE_FREQUENCIES
from modules.frequency_module import Q_OPTIONS
from modules.frequency_module import RANDOMIZATION_MODES
from modules.frequency_module import SAMPLE_OPTIONS
from modules.frequency_module import THIRD_OCTAVE_FREQUENCIES
from modules.frequency_module import create_modified_audio
from modules.frequency_module import create_automobile_conditioned_audio
from modules.frequency_module import create_passthrough_audio
from modules.frequency_module import create_trial_audio
from modules.frequency_module import get_frequency_options
from modules.frequency_module import get_practice_gain_options
from modules.frequency_module import resolve_no_change_probability
from modules.frequency_module import resolve_trial_parameters

