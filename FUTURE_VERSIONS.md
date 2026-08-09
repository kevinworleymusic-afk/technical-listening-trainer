# Future Versions — Technical Listening Trainer

This file tracks planned features, module additions, and platform improvements for future releases. Items are grouped by category and ordered roughly by priority or logical dependency.

---

## Version 1.x — Shared engine improvements (EQ module foundation)

These features extend what the EQ / Band Identification module already does and lay groundwork for every module that follows.

Current status note:
- Basic automobile listening conditioning is now available in the EQ module (cabin profile, AC profile, loudness preset, and one-click scenario presets).
- Versioned roadmap items below focus on deepening realism, analysis, and module specialization beyond this baseline.

- **Adaptive difficulty** — automatically tighten or widen the gain/frequency range based on rolling accuracy so the session always stays in the productive zone of effort
- **Threshold estimation** — formal threshold-seeking procedure (e.g., 2-up / 1-down staircase) to measure the minimum audible change for a given parameter at a given Q and source material
- **Session history viewer** — in-app review of past CSV exports with per-condition accuracy breakdown (frequency band, gain magnitude, Q, band mode)
- **Results plots** — histogram or confusion-matrix view of identification accuracy by frequency band; accuracy vs. gain-magnitude chart
- **Trial count goal** — set a target number of trials for a session and display progress toward it
- **Cross-platform audio playback** — replace macOS `afplay` with a Python-native playback library (e.g., sounddevice or pygame.mixer) so the app runs on Windows and Linux without modification
- **Headless / CLI test runner** — run a batch of scored trials without the GUI for scripted self-testing and data collection

---

## Version 2.0 — Tonal Attributes module

Train recognition of broad tonal color changes that mimic loudspeaker voicing differences and crossover slope effects.

- Shelf filters (low shelf, high shelf) with selectable corner frequency and gain
- Filter slope variations (6 dB/oct, 12 dB/oct)
- Brightness, warmth, and "nasality" preset ranges as named starting points
- Blind A/B detection and identification modes matching the EQ module structure

---

## Version 3.0 — Noise & Artifacts module

Train identification of common audio defects that appear in audio-system evaluation.

- Broadband noise floor injection at selectable SNR levels
- Band-limited hiss simulation (e.g., HF-only noise)
- Clipping / hard saturation at selectable thresholds
- Quantization noise (bit-depth reduction simulation)
- Dropout / intermittent silence events
- Detection mode: does a defect exist?
- Identification mode: which defect type is present?

---

## Version 4.0 — Spatial Balance & Stereo Imaging module

Train sensitivity to left/right balance and stereo width differences common in automotive-audio evaluation.

- Left/right level imbalance in configurable dB steps
- Front/rear balance offset (4-channel panning)
- Stereo width manipulation (mid/side gain adjustment)
- Mono collapse simulation
- Localization shift: phantom-image displacement left or right of center
- Identification mode: direction and magnitude of imbalance

---

## Version 5.0 — Reverberation module

Train recognition of reverb characteristics relevant to listening-room acoustics and automotive cabin simulation.

- Simulated RT60 values (short, medium, long decay) via convolution or algorithmic reverb
- Early reflections vs. late reverb separately controlled
- Room size / pre-delay variation
- Detection: more or less reverb than reference?
- Identification: estimate RT60 category or pre-delay amount

---

## Version 6.0 — Level & Channel Balance module

Develop precise level-matching skills needed for gain-matching in AB tests and system alignment.

- Fine level offsets (0.5 dB – 6 dB steps)
- Channel-specific level changes (left only, right only, or both)
- Detection mode: which sample is louder?
- Identification mode: estimate the dB offset

---

## Version 7.0 — Time Alignment / Delay module

Train detection of mis-alignment between drivers or channels, a critical skill in automotive-audio system tuning.

- Absolute delay added to one channel (0.1 ms – 10 ms range)
- Relative inter-channel delay between left and right
- Detection: is the modified sample time-aligned or delayed?
- Identification: estimate the delay amount in ms

---

## Version 8.0 — Polarity & Phase module

Train recognition of polarity inversion and frequency-dependent phase errors.

- Full polarity inversion (one channel or both)
- All-pass filter phase rotation at selectable corner frequency
- Detection: same or inverted polarity?
- Identification: which channel is inverted?

---

## Version 9.0 — Crossover Integration module

Train recognition of crossover-induced artifacts relevant to multi-way speaker systems and automotive DSP alignment.

- Crossover frequency variation (simulated high-pass / low-pass pair)
- Overlap and gap between driver bands
- Phase discontinuity at crossover point
- Detection: does the crossover region sound smooth or discontinuous?

---

## Version 10.0 — Bass / Subwoofer Integration module

Focus training on the low-frequency range where automotive-audio integration challenges are most common.

- Sub level offset relative to mains
- Subwoofer low-pass corner frequency variation
- Group-delay differences between sub and mains
- Detection and identification modes for level, corner frequency, and alignment

---

## Version 11.0 — Resonance Detection module

Train the ability to identify narrow resonances that appear in cabinet, vehicle-panel, or port tuning issues.

- High-Q peaking boost at selectable frequency (simulates a resonant mode)
- Ring-down / decay tail simulation
- Detection: is a resonance present?
- Identification: estimate resonance frequency

---

## Version 12.0 — Distortion Detection module

Train identification of harmonic and intermodulation distortion from amplifiers and transducers.

- 2nd-order harmonic distortion at selectable THD level
- 3rd-order harmonic distortion
- Intermodulation distortion (two-tone IM simulation)
- Detection: clean or distorted?
- Identification: distortion type and approximate level

---

## Version 13.0 — SNR & Masking module

Train perception of signal-to-noise ratio and auditory masking, relevant to automotive noise floor evaluation.

- Broadband masking noise at selectable level below signal
- Band-specific masking (low-frequency road noise simulation)
- Detection: can you hear the target signal through the noise?
- Threshold-seeking mode: find the minimum SNR at which the signal is audible

---

## Version 14.0 — Vehicle-Noise Masking module

Specialized module using recorded or simulated vehicle noise as the masking stimulus.

- Road-noise convolution with user-supplied impulse responses or noise recordings
- Wind-noise overlay at selectable speed/level
- Advanced HVAC noise simulation with speed/fan-band modeling
- Evaluate how EQ changes affect intelligibility and perceived quality in a noisy cabin environment

---

## Version 15.0 — Dynamics / Compression module

Train detection and identification of dynamic processing artifacts.

- Compressor ratio and threshold variation
- Attack and release time variation
- Pumping/breathing artifact simulation
- Detection: compressed or uncompressed?
- Identification: estimate ratio or attack character

---

## Version 16.0 — Multichannel Fault Identification module

Full-system diagnostic listening for multi-channel audio setups (4-, 6-, or 8-channel automotive systems).

- Single-channel dropout or mute
- Per-channel EQ offset
- Mixed multichannel polarity faults
- Identification: which channel is faulted and what is the fault type?

---

## Version 17.0 — Combined Diagnostic Listening module

Integrate all previous modules into a unified diagnostic test sequence.

- Random module rotation: each trial draws from any enabled module
- Fault-type identification across the full vocabulary of defects
- Difficulty scaling across modules simultaneously
- Comprehensive session report covering all module categories

---

## Platform and infrastructure backlog

These items apply across all versions and can be developed incrementally alongside any module work.

| Item | Notes |
|---|---|
| Pluggable module architecture | Each module registers itself with a shared experiment engine; `listening_test.py` becomes a launcher |
| Shared experiment engine | Common trial orchestration, randomization, scoring, adaptive-difficulty, and logging logic consumed by all modules |
| Automated test suite | Coverage for filter response accuracy, A/B randomization, scoring logic, adaptive staircase, and CSV export |
| Configuration file / preset system | Save and restore full control-panel states between sessions |
| In-app session history browser | Review past sessions without leaving the application |
| Accuracy-by-condition heat map | Visual breakdown of correct vs. incorrect by frequency, gain, Q, or other parameter |
| Multi-platform packaging | Bundle into a standalone `.app` / `.exe` / AppImage with no Python installation required |
| Audio device selection | Choose output device from within the app instead of relying on the system default |
| Keyboard shortcuts | Trigger Sample A, Sample B, Yes/No, and Create Trial without touching the mouse |
| Dark mode UI | Optional dark theme for low-light listening environments |
