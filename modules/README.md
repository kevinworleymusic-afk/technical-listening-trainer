# Listening Modules

This folder now contains standalone module files so users can download only what they need.

## Current downloadable modules

1. `frequency_module.py`
- Purpose: Frequency/EQ-specific trial logic and DSP.
- Includes: band options, frequency pools, gain/Q options, randomization rules, trial parameter resolution, and modified-audio rendering.
- Primary API:
	- `get_frequency_options(band_mode)`
	- `resolve_trial_parameters(selected_values, lock_values, randomization_mode)`
	- `create_trial_audio(input_file, output_file, selected_values, lock_values, randomization_mode)`
	- `create_modified_audio(input_file, output_file, frequency, gain_db, q)`

2. `additional_module.py`
- Purpose: Non-frequency extension parameter resolution for future installs.
- Includes: generic lock/randomization helpers for additional parameters.
- Primary API:
	- `should_randomize(randomization_mode, is_locked)`
	- `resolve_additional_parameters(selected_values, lock_values, option_map, randomization_mode)`

## Compatibility note

`audio_processing.py` re-exports frequency-module APIs so existing imports keep working.

## Simple import examples

```python
from modules.frequency_module import create_trial_audio
from modules.additional_module import resolve_additional_parameters
```

## Roadmap modules

Planned modules include tonal attributes, noise and artifacts, spatial balance, reverberation, time alignment, imaging/localization, polarity/phase, crossover integration, bass integration, resonance detection, distortion, masking, dynamics, multichannel fault identification, and combined diagnostic listening.
