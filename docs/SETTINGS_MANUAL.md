# Current Settings Manual

This manual documents every current user-facing setting in the application (`listening_test.py`) as currently implemented.

## Access points

- Launch app: `python listening_test.py`
- Main-screen settings:
  - **Test Mode**
  - **Change/No-Change Mix** (Mode 1)
  - **Identify** target (Mode 2)
- Full settings window:
  - Click **Open Settings**
  - Tabs: **Trial Settings**, **Session Tracking**, **Waveform Selector**, **Boost / Cut**
  - Click **Save And Close** to hide window while keeping selected values

---

## Main response settings

### 1) Test Mode
- Label: **Test Mode**
- Options:
  - `Mode 1: Detect Change`
  - `Mode 2: Identify Setting`
- Default: `Mode 1: Detect Change`
- Effect:
  - Mode 1 enables Yes/No detection workflow
  - Mode 2 enables identification-answer workflow

### 2) Change/No-Change Mix (Mode 1)
- Label: **Change/No-Change Mix**
- Options: `Random`, `0%`, `25%`, `50%`, `75%`
- Default: `Random`
- Effect:
  - Controls no-change trial probability for Mode 1
  - Disabled when Mode 2 is active

### 3) Identify target (Mode 2)
- Label: **Identify**
- Options: `Frequency`, `Q`, `Gain`
- Default: `Frequency`
- Effect:
  - Sets which parameter the mode-2 answer dropdowns ask for
  - Disabled when Mode 1 is active

---

## Settings window: Waveform Selector tab

### 4) Auto-Select Length (sec)
- Label: **Auto-Select Length (sec)**
- Options: `3`, `5`, `8`, `10`, `15`, `20`, `30`
- Default: `8`
- Effect:
  - Sets analysis window length used by **Auto-Pick Loud Section**

---

## Settings window: Trial Settings tab

### 5) Randomization Mode
- Label: **Randomization Mode**
- Options:
  - `Randomize Unlocked`
  - `Randomize All`
  - `Use Selected Values`
- Default: `Randomize Unlocked`
- Effect:
  - `Randomize Unlocked`: randomizes only controls not locked
  - `Randomize All`: ignores lock toggles and randomizes all randomizable fields
  - `Use Selected Values`: keeps selected values fixed

### 6) Frequency Bands (+ lock)
- Label: **Frequency Bands**
- Options:
  - `1 Octave`
  - `1/3 Octave`
- Default: `1 Octave`
- Lock checkbox default: **Off**
- Effect:
  - Chooses frequency list used by frequency/range controls and frequency answers

### 7) Practice Frequency Range (Hz) (+ lock)
- Label: **Practice Frequency Range (Hz)**
- Two dropdowns:
  - **Start** and **End** from the active band list
- Defaults (with `1 Octave`): Start `125`, End `16000`
- Lock checkbox default: **On**
- Effect:
  - When lock is on, randomized frequency selection is constrained to this range
  - When lock is off, full band list is used
  - If Start > End, values are automatically reordered

### 8) Frequency (Hz) (+ lock)
- Label: **Frequency (Hz)**
- Options:
  - `1 Octave`: `125, 250, 500, 1000, 2000, 4000, 8000, 16000`
  - `1/3 Octave`: `125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000`
- Default: `1000`
- Lock checkbox default: **Off**
- Effect:
  - Selected frequency is used directly when frequency is not randomized

### 9) Q Factor (+ lock)
- Label: **Q Factor**
- Options: `0.5`, `1`, `2`, `4`, `8`
- Default: `1.0`
- Lock checkbox default: **Off**
- Effect:
  - Sets or constrains EQ bandwidth value(s)

---

## Settings window: Boost / Cut tab

### 10) Gain (+ lock)
- Label: **Gain**
- Options: `-12` to `+12` dB (including `0`)
- Default: `+6`
- Lock checkbox default: **Off**
- Effect:
  - Base gain value used when gain is not randomized

### 11) Gain Direction
- Label: **Gain Direction**
- Options:
  - `Boost and Cut`
  - `Boost Only`
  - `Cut Only`
- Default: `Boost and Cut`
- Effect:
  - Limits which filter types are allowed
  - Dynamically disables incompatible count/range controls

### 12) Cut Count
- Label: **Cut Count**
- Options: dynamic `0..N` (bounded by total filter cap)
- Default: `0`
- Effect:
  - Number of cut filters per trial

### 13) Boost Count
- Label: **Boost Count**
- Options: dynamic `0..N` (bounded by total filter cap)
- Default: `1`
- Effect:
  - Number of boost filters per trial

Count-rule behavior:
- Total filters are capped at **3**
- If both counts are set to `0`, app auto-corrects to one boost
- In `Boost Only`, cut count is forced to `0`, and boost count is at least `1`
- In `Cut Only`, boost count is forced to `0`, and cut count is at least `1`

### 14) Cut Gain Range (dB)
- Label: **Cut Gain Range (dB)**
- Start/End options: `-12` to `-1`
- Defaults: Start `-12`, End `-1`
- Effect:
  - Constrains randomized cut gains when cut side is active
  - Disabled when cut side is inactive
  - Start/End auto-reordered if reversed

### 15) Exact Cut Amount (dB) (+ lock)
- Label: **Exact Cut Amount (dB)**
- Options: `-12` to `-1`
- Default: `-12`
- Lock checkbox default: **Off**
- Effect:
  - When locked, cut-side randomization uses only this cut value
  - Disabled when cut side is inactive

### 16) Boost Gain Range (dB)
- Label: **Boost Gain Range (dB)**
- Start/End options: `+1` to `+12`
- Defaults: Start `+1`, End `+12`
- Effect:
  - Constrains randomized boost gains when boost side is active
  - Disabled when boost side is inactive
  - Start/End auto-reordered if reversed

### 17) Exact Boost Amount (dB) (+ lock)
- Label: **Exact Boost Amount (dB)**
- Options: `+1` to `+12`
- Default: `+1`
- Lock checkbox default: **Off**
- Effect:
  - When locked, boost-side randomization uses only this boost value
  - Disabled when boost side is inactive

---

## Settings window: Session Tracking tab

These are session controls rather than randomization parameters, but they are part of the current settings window:

- **Start New Session**: clears score data and removes generated audio files (`modified.wav`, `match_guess.wav`, `memorization.wav`, `selected_section.wav`) if present
- **Reset Session Stats**: clears in-memory scoring/session results
- **Export Session Results**: writes current session results to CSV via save dialog

---

## Lock behavior summary

Lock checkboxes currently available:
- Frequency Bands lock
- Practice Frequency Range lock
- Frequency lock
- Q lock
- Gain lock
- Exact Cut lock
- Exact Boost lock

Operational summary:
- In `Randomize Unlocked`, lock state determines whether each setting is held or randomized
- In `Randomize All`, lock state is ignored for randomization decisions
- In `Use Selected Values`, randomization is disabled and selected values are used directly

