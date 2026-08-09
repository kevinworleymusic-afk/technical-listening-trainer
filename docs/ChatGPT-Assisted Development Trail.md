# ChatGPT-Assisted Development Trail

## Technical Listening Trainer

### Documentation Note

This document is a retrospective record of the early development of the
Technical Listening Trainer.

During the initial prototype period, development was performed interactively
with ChatGPT while writing, running, debugging, and testing the Python
application locally. A formal GitHub feature-branch and pull-request workflow
had not yet been adopted.

This record was reconstructed from the contemporaneous ChatGPT development
conversation and the resulting project state. It is intended to document the
development process accurately rather than recreate Git history that did not
exist at the time.

---

# Phase 1: Initial Listening-Test Prototype

## Objective

Create a basic blind listening-test application capable of comparing an
unmodified reference audio file against a processed version.

## Development Work

The initial application was developed in Python using Tkinter for the GUI.

The prototype included:

- Reference-audio playback
- Sample A playback
- Sample B playback
- Stop-audio control
- New Trial control
- Blind A/B presentation
- Random assignment of the modified file to A or B

During each trial, one button represents the original reference and the other
represents the processed stimulus. The assignment is randomized when a new
trial is generated and remains fixed during that trial.

## Development / Debugging Issues

Early testing included troubleshooting:

- File-path behavior
- Audio continuing to play after leaving the application
- Correct routing of reference and modified files
- Verifying that A/B randomization changed assignment rather than changing the
  underlying test condition unexpectedly

Playback was ultimately handled through a separate `afplay` process so that
the Tkinter application remained responsive.

---

# Phase 2: Separating DSP from the GUI

## Objective

Move audio-processing operations out of the main listening-test application
so that DSP code could be developed independently from GUI and experiment
logic.

## Architecture

The application was separated into two primary Python components:

- `listening_test.py`
  - GUI
  - playback
  - trial creation
  - A/B assignment
  - user-selected test parameters

- `audio_processing.py`
  - audio loading
  - filter generation
  - signal processing
  - modified-audio output

The listening-test application calls the processing function and passes the
parameters required to create the current stimulus.

This became the first step toward the later shared-engine / modular DSP
architecture.

---

# Phase 3: Python Audio Processing

## Objective

Generate an audibly and numerically modified reference signal using controlled
EQ.

## Libraries / Tools

The processing implementation used:

- NumPy
- SciPy signal processing
- SoundFile

SoundFile installation/import behavior was addressed during initial setup.

The DSP script successfully generated:

`modified.wav`

from the selected reference material.

## DSP Verification

Processing was not accepted solely on the basis of hearing a difference.

A test condition requested approximately:

- Center frequency: 2000 Hz
- Gain: +6 dB

Numerical analysis produced:

- Peak frequency: 2002.587890625 Hz
- Peak gain: +5.999821625 dB
- Maximum sample difference: 0.251642384

This provided numerical confirmation that the requested EQ operation was being
applied and that the processed waveform differed from the source.

---

# Phase 4: Randomized EQ Trials

## Objective

Expand the prototype from a single predetermined processing condition into a
repeatable technical-listening exercise.

## Added Functionality

Trial generation was expanded so that EQ frequency could change between
trials.

Instead of repeatedly comparing the same processed condition, a new trial
could select another EQ center frequency and generate a corresponding
processed stimulus.

This changed the application from a simple A/B demonstration into the
beginning of an actual frequency-identification training system.

---

# Phase 5: Frequency-Band Modes

## Objective

Allow frequency-identification training at different resolutions.

Two frequency-spacing modes were introduced.

### 1-Octave Mode

Current frequency set:

- 250 Hz
- 500 Hz
- 1 kHz
- 2 kHz
- 4 kHz
- 8 kHz

### 1/3-Octave Mode

Current frequency set:

- 250 Hz
- 315 Hz
- 400 Hz
- 500 Hz
- 630 Hz
- 800 Hz
- 1 kHz
- 1.25 kHz
- 1.6 kHz
- 2 kHz
- 2.5 kHz
- 3.15 kHz
- 4 kHz
- 5 kHz
- 6.3 kHz
- 8 kHz

The GUI allows the desired frequency-spacing mode to be selected before trial
generation.

---

# Phase 6: Adjustable Gain

## Objective

Allow the listener to control the magnitude and direction of the EQ change.

Positive and negative gain values were introduced so that the same system
could generate both:

- EQ boosts
- EQ cuts

Example selectable values included:

+15, +12, +9, +6, +3, +2, +1,
-1, -2, -3, -6, -9, -12, and -15 dB.

This created another difficulty dimension independent of frequency.

---

# Phase 7: Adjustable Q Development

## Objective

Expand the EQ module so that filter bandwidth can also be controlled.

The original DSP implementation used a fixed Q.

Development then began on passing Q through the same parameter path used by
frequency and gain:

GUI Q selection
→ listening-test variable
→ `create_modified_audio()`
→ DSP filter calculation

Planned/selectable Q values include:

- 0.5
- 1
- 2
- 4
- 8

This allows future exercises to range from broad tonal changes to narrow
resonances.

At the point represented by this retrospective record, adjustable Q was still
being integrated/tested rather than considered a completed Module 1 feature.

---

# Phase 8: Project Expansion

As the EQ prototype developed, the scope of the project was expanded from one
listening exercise into a modular Technical Listening Trainer.

The architectural concept became:

Shared Experiment Engine
→ Individual Listening Modules
→ Shared DSP Functions
→ Results / Analysis

System-wide features planned for the shared engine include:

- Blind A/B randomization
- Adjustable difficulty
- Adaptive threshold testing
- Scoring
- Trial counting
- Session logging
- CSV export
- Session history
- Accuracy by condition
- Threshold estimation
- Results summaries
- Performance visualization

These capabilities are intended to be implemented once and reused across
listening modules.

---

# Phase 9: Module Roadmap

The broader project roadmap was defined to include:

1. Band / EQ Identification
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

The later modules extend the project toward automotive audio evaluation and
system-diagnostic listening.

---

# Phase 10: Repository Architecture

As the project grew beyond the original prototype, a dedicated
`technical-listening-trainer` repository was established.

The developing repository structure separates responsibilities into:

- `app/` - GUI and application control
- `dsp/` - reusable signal-processing functions
- `modules/` - individual listening exercises
- `results/` - generated session/result data
- `tests/` - software and DSP validation
- `docs/` - specifications, roadmap, architecture, and development records

The original Python files were reorganized around this architecture while
preserving the working prototype.

---

# Current Transition

The initial prototype period relied primarily on:

ChatGPT-assisted planning/debugging
→ local implementation
→ manual testing
→ Git commits

The project is now transitioning toward a more formal development workflow:

Requirement / feature
→ GitHub feature branch
→ implementation
→ testing
→ commit(s)
→ pull request
→ review / merge to main

GitHub Copilot is also being used during implementation and is documented
separately in the Copilot development trail.

---

# Post-Prototype Additions: Automobile Listening Simulation

After the original prototype phases documented above, the project added an
automobile listening simulation section to better emulate in-car evaluation
conditions during EQ training.

Implemented additions include:

- Automobile settings tab in the GUI
- Cabin-condition profiles (parked, city, highway, windows-open styles)
- AC noise overlays (off/low/medium/high)
- Loudness presets for practical in-car monitoring levels
- One-click preset application for common scenarios
- Conditioned A/B rendering that applies the same noise seed to both samples
  so trial fairness is preserved

These additions are implemented in the current codebase and tracked in the
Copilot worklog as part of the ongoing transition from prototype workflow to
structured, module-oriented development.

---

# AI-Assistance Disclosure

ChatGPT was used during the prototype period as an interactive development
assistant for:

- Breaking features into implementation steps
- Explaining Python behavior
- Troubleshooting errors
- Discussing software architecture
- Designing DSP parameter flow
- Developing testing approaches
- Interpreting numerical verification results
- Planning additional listening modules
- Git / GitHub workflow guidance

The application was developed iteratively by editing and running the code
locally, evaluating program behavior, reporting results/errors, and making
subsequent implementation decisions.

AI assistance is documented here to distinguish development assistance from
the actual software implementation, testing, and engineering decisions
represented by the repository.

---

# Historical Record Policy

This document should not be interpreted as a substitute for Git commit
history.

For the early prototype period, it provides a retrospective record based on
the contemporaneous development workflow.

For subsequent development, Git branches, commits, pull requests, tests, and
the development documentation should serve as the primary engineering record.