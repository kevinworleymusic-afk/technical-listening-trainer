# DSP Layer

This folder is intended for reusable signal-processing code that generates controlled listening-test stimuli.

Current implementation note:
- The active DSP engine currently lives in `modules/frequency_module.py` and is re-exported by `audio_processing.py`.
- It includes peaking-EQ trial rendering plus automobile conditioning layers (cabin noise profile, AC noise profile, loudness preset, peak limiting, seeded trial conditioning).

As the prototype is refactored further, DSP code can be moved here once imports are updated safely. Future DSP components may include delay, level manipulation, polarity/phase processing, crossover simulation, distortion, extended vehicle-noise masking using recordings/IRs, and dynamics processing.
