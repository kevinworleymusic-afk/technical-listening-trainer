# Technical Listening Trainer

Python-based technical critical-listening training platform for audio-system evaluation, psychoacoustics, DSP development, and automotive-audio preparation.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/kevinworleymusic-afk/technical-listening-trainer.git
cd technical-listening-trainer

# 2. Install dependencies
pip install numpy scipy soundfile

# 3. Launch the app
python listening_test.py
```

> **Note:** Requires Python 3.x and macOS (audio playback uses `afplay`). `tkinter` ships with the standard Python installer — no separate install needed.

---

## Current module — EQ / Band Identification

The first fully implemented module trains the ear to detect and identify parametric EQ changes applied to a user-supplied audio source.

### Audio source controls

- Load any WAV, AIFF, or FLAC file as the reference signal
- Interactive waveform display with a visual selection overlay
- Manual section selection: click once for start, click again for end
- Auto-pick loud section: energy-based sliding-window detection runs in a background thread and animates a spinner while searching
- Configurable section length (3 s – 30 s) used by the auto-picker
- Clear section to revert to the full file

### EQ / filter controls

| Control | Details |
|---|---|
| Band mode | 1 Octave (8 center frequencies, 125 Hz – 16 kHz) or 1/3 Octave (22 center frequencies, 125 Hz – 16 kHz) |
| Frequency range | Constrain randomized frequency selection to a user-defined min–max span |
| Cut count | 0 – 3 simultaneous cut filters per trial |
| Boost count | 0 – 3 simultaneous boost filters per trial (combined max of 3 across cuts and boosts) |
| Gain direction | Boost and Cut, Boost Only, or Cut Only |
| Cut range | Randomization constrained to a selected dB range (−1 dB – −12 dB) |
| Boost range | Randomization constrained to a selected dB range (+1 dB – +12 dB) |
| Exact cut / Exact boost | Pin a specific dB value to lock in for cut or boost |
| Q value | 0.5, 1, 2, 4, or 8 — selectable and lockable per trial |
| Randomization mode | Randomize Unlocked, Randomize All, or Use Selected Values |

Individual parameters can be locked with checkboxes so they stay fixed while everything else randomizes.

### DSP engine

- Second-order peaking EQ (IIR biquad) applied with `scipy.signal.lfilter`
- Coefficients computed analytically from Audio EQ Cookbook formulas
- Per-filter peak frequency and gain validated via `scipy.signal.freqz` after each filter is designed
- Passthrough path for no-change trials (bit-exact copy of source)
- Up to 3 independent peaking filters chained in a single trial, each with its own frequency, gain, and Q

### Test modes

**Mode 1 – Detect Change**

- Blind A/B comparison: Sample A and Sample B are randomly assigned to the reference and modified signals each trial
- User selects Yes or No (did A and B sound different?), then clicks Submit Answer
- Scored as Hit, Miss, False Alarm, or Correct Reject
- Configurable no-change probability: 0 %, 25 %, 50 %, or 75 % of trials present no EQ change

**Mode 2 – Identify Setting**

- Identification target is selectable: Frequency, Q, or Gain
- One dropdown answer selector per active filter (up to 3), labeled by the number of active changes
- User picks the answer value(s) and clicks Check Answers
- Partial credit: matched count vs. total target count is shown when only some answers are correct
- Answers are compared using unordered set matching

### Study / match tools

- **Render & play reference example** — renders a deterministic study copy with the current locked settings so you can hear what the target sounds like before practicing
- **Render & play answer guess** — substitutes your guessed value(s) into the current trial's filters and renders an audio comparison so you can hear how close your answer sounds

### Automobile listening simulation

- Dedicated Automobile settings tab with one-click preset workflow
- Enable/disable automobile conditioning for trial playback
- Cabin-condition profiles: Off, Parked Cabin, City Streets, Highway Cruise, Windows Open
- Air-conditioning overlays: Off, Low, Medium, High
- Loudness presets: Reference, Comfort, Commute, Loud
- One-click presets: Neutral Cabin, City Commute, Highway With AC, Windows Open Loud
- Fair A/B behavior: both Sample A and Sample B use the same conditioning seed in a trial so only the EQ change differs

### Automobile quick start

1. Open **Settings** and go to the **Automobile** tab.
2. Set **Automobile Simulation** to **On**.
3. Choose a preset and click **Apply Preset**:
	- **City Commute**: balanced daily-driving profile for general practice
	- **Highway With AC**: stronger masking for tougher discrimination
	- **Windows Open Loud**: most difficult profile with aggressive masking
4. Generate a new trial and compare **Sample A** vs **Sample B**.
5. If needed, switch to another preset and generate a fresh trial.

Recommended progression:
- Start with **Neutral Cabin** to calibrate your hearing to the workflow.
- Move to **City Commute** for regular drills.
- Use **Highway With AC** and **Windows Open Loud** for advanced training.

### Session tracking and export

- Live status panel: displays all selected controls, lock states, active trial parameters, and last response feedback in real time
- Per-answer session log: captures scored responses with trial metadata and score detail (for example, 2/3 in Mode 2)
- Session statistics: answered count, correct count, accuracy %, and detection breakdown (Hits, Misses, False Alarms, Correct Rejects) plus mode-2 matched target count
- Score display updated after each response
- Export session to CSV (standard file-save dialog, timestamped default filename, defaults to `results/`; exports scored-answer rows)
- Reset session stats and clear generated audio files for a clean start
- New session button removes all generated WAV files from the working directory

---

## Project structure

```
technical-listening-trainer/
├── app/
│   └── common_gui.py       # Shared Tkinter layout helpers and theme constants
├── dsp/                    # Future home for reusable DSP stimulus-generation code
├── docs/                   # Project briefs, architecture notes, methodology documents
├── modules/
│   ├── frequency_module.py # EQ frequency/gain/Q options, trial generation, and automobile conditioning DSP
│   └── additional_module.py# Generic helper for non-frequency module parameters
├── results/                # Generated session CSV exports and analysis outputs
├── tests/                  # Automated tests for DSP, randomization, scoring, and experiment logic
├── audio_processing.py     # Compatibility facade re-exporting frequency_module APIs
└── listening_test.py       # Main GUI application entry point
```

---

## Dependencies

- Python 3.x
- [NumPy](https://numpy.org/) — array operations and waveform math
- [SciPy](https://scipy.org/) — IIR filter design (`signal.lfilter`, `signal.freqz`)
- [soundfile](https://python-soundfile.readthedocs.io/) — audio file read/write (WAV, AIFF, FLAC)
- [tkinter](https://docs.python.org/3/library/tkinter.html) — GUI (included in standard Python on macOS and most Linux distributions)

Audio playback uses `afplay` (macOS system command). See [FUTURE_VERSIONS.md](FUTURE_VERSIONS.md) for cross-platform playback plans.

---

## Future versions

Planned listening modules, shared engine features, and platform improvements are tracked in **[FUTURE_VERSIONS.md](FUTURE_VERSIONS.md)**.

## Settings manual

For a complete, current reference of all configurable controls in the app, see **[docs/SETTINGS_MANUAL.md](docs/SETTINGS_MANUAL.md)**.
