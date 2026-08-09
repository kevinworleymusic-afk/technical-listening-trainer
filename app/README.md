# Application Layer

This folder is intended for GUI, playback control, trial state, and shared experiment-flow code.

`common_gui.py` is the main shared GUI file for reusable controls/layout patterns across modules.
Additional listening modules should build their UI from these helpers rather than duplicating Tk layout code.

Current GUI feature coverage (implemented in `listening_test.py`) includes:
- trial controls, waveform section picker, and session tracking tabs
- automobile simulation tab with cabin/AC/loudness settings
- one-click automobile preset application for common listening scenarios

As the prototype is refactored, `listening_test.py` can be moved here once imports and local development paths are updated safely.
