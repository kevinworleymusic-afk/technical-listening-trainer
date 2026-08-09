# Technical Listening Trainer

Python-based technical critical-listening training platform for audio-system evaluation, psychoacoustics, DSP development, and automotive-audio preparation.

## Current status

The first working module focuses on EQ / band identification. It currently supports blind A/B assignment, randomized frequency selection, selectable 1-octave and 1/3-octave frequency sets, and selectable positive/negative gain values.

The codebase now separates module logic so users can download focused components:
- `modules/frequency_module.py` for frequency/EQ options and DSP trial generation.
- `modules/additional_module.py` for non-frequency extension parameter handling.
- `audio_processing.py` as a compatibility facade re-exporting frequency APIs.

## Project structure

- `app/` – GUI and trial-control code
- `dsp/` – signal-processing functions used to generate listening stimuli
- `docs/` – project briefs, architecture notes, methodology, and design documentation
- `modules/` – listening-module definitions and future module-specific logic
- `results/` – generated listening-test results and analysis outputs (data files should remain privacy-safe)
- `tests/` – automated verification of DSP, randomization, scoring, and experiment logic

## Shared system features planned

Blind A/B randomization, adjustable difficulty, adaptive threshold testing, scoring, trial count, session logging, CSV export, session history, accuracy by condition, threshold estimation, and results summaries/plots.

## Listening-module roadmap

1. EQ / Band Identification
2. Tonal Attributes
3. Noise & Artifacts
4. Spatial Balance
5. Reverberation
6. Level & Channel Balance
7. Time Alignment / Delay
8. Stereo Imaging & Localization
9. Polarity & Phase
10. Crossover Integration
11. Bass / Subwoofer Integration
12. Resonance Detection
13. Distortion Detection
14. SNR & Masking
15. Vehicle-Noise Masking
16. Dynamics / Compression
17. Multichannel Fault Identification
18. Combined Diagnostic Listening

The long-term goal is an extensible technical-listening platform where each auditory module plugs into a shared experiment engine for stimulus generation, randomization, scoring, adaptive difficulty, logging, and analysis.
