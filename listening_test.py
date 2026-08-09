import tkinter as tk
import subprocess
import random 

from audio_processing import create_modified_audio

modified_file = "modified.wav"
reference_file = "Tracy_Chapman_Fast_car.wav"

audio_process = None
modified_sample = None

gain_options = [-12, -6, -3, -2, -1, 0, 1, 2, 3, 6, 12]  # dB

octave_frequencies = [250, 500, 1000, 2000, 4000, 8000]  # Hz

third_octave_frequencies = [
    250, 315, 400, 500, 630, 800, 
    1000, 1250, 1600, 2000, 2500, 3150, 
    4000, 5000, 6300, 8000, 10000, 12500, 16000]  # Hz

current_frequency = None
current_gain = 6

#1.  Functions
def play_reference():
    global audio_process

    if audio_process is not None:
        audio_process.terminate()

    audio_process = subprocess.Popen(["afplay", "Tracy_Chapman_Fast_car.wav"])

def stop_audio():
    global audio_process

    if audio_process is not None:
        audio_process.terminate()
        audio_process = None

def create_trial():
    global modified_sample
    global current_frequency
    global current_gain

    modified_sample = random.choice(["A", "B"])

    current_gain = selected_gain.get()

    if selected_band_mode.get() == "1 Octave":
        frequency_pool = octave_frequencies
    else:
        frequency_pool = third_octave_frequencies

    current_frequency = random.choice(frequency_pool)

    create_modified_audio(
        current_frequency,
        current_gain
    )

    print("Modified sample:", modified_sample)
    print("Frequency:", current_frequency, "Hz")
    print("Gain:", current_gain, "dB")
    print("Band mode:", selected_band_mode.get())

def play_sample_a():
    global audio_process

    if audio_process is not None:
        audio_process.terminate()

    if modified_sample == "A":
        filename = modified_file
    else:
        filename = reference_file

    audio_process = subprocess.Popen(["afplay", filename])

def play_sample_b():
    global audio_process

    if audio_process is not None:
        audio_process.terminate()

    if modified_sample == "B":
        filename = modified_file
    else:
        filename = reference_file

    audio_process = subprocess.Popen(["afplay", filename])

#2. Main Window. 
root = tk.Tk()

selected_gain = tk.IntVar(value=6)
selected_band_mode = tk.StringVar(value="1 Octave")

root.title("Critical Listening Study")
root.geometry("600x400")

#3. Application Button Labels
title_label = tk.Label(
    root,
    text="Critical Listening Study",
    font=("Arial", 20)
)
title_label.pack(pady=30)

#Line 1 of GUI

reference_label = tk.Label(
    root,
    text="Reference Audio",
    font=("Arial", 14)
)

reference_label.pack(
    anchor="w",
    padx=30, 
    pady=(15,1)
)

button_frame = tk.Frame(root)
button_frame.pack(
    anchor="w", 
    padx=30, 
    pady=(0, 5) 
    )

play_reference_button = tk.Button(
    button_frame,
    text="Play",
    command=play_reference
)
play_reference_button.pack(side="left", padx=5)

stop_button = tk.Button(
    button_frame,
    text="Stop",
    command=stop_audio
)
stop_button.pack(side="left", padx=5)

#Line 2 of GUI

trial_label = tk.Label(
    root,
    text="Trial Audio",
    font=("Arial", 14)
)
trial_label.pack(
    anchor="w",
    padx=30,
    pady=(20, 1)
)

trial_button_frame = tk.Frame(root)
trial_button_frame.pack(
    anchor="w",
    padx=30,
    pady=(0, 5)
)

sample_a_button = tk.Button(
    trial_button_frame,
    text="Play Sample A",
    command=play_sample_a
)
sample_a_button.pack(side="left", padx=(0, 5))

sample_b_button = tk.Button(
    trial_button_frame,
    text="Play Sample B",
    command=play_sample_b
)
sample_b_button.pack(side="left", padx=5)

settings_label = tk.Label(
    root,
    text="Trial Settings",
    font=("Arial", 14)
)
settings_label.pack(
    anchor="w",
    padx=30,
    pady=(20, 5)
)

gain_label = tk.Label(
    root,
    text="Gain:"
)
gain_label.pack(
    anchor="w",
    padx=30
)

gain_menu = tk.OptionMenu(
    root,
    selected_gain,
    *gain_options
)
gain_menu.pack(
    anchor="w",
    padx=30,
    pady=(0, 10)
)

band_label = tk.Label(
    root,
    text="Frequency Bands:"
)
band_label.pack(
    anchor="w",
    padx=30
)

band_menu = tk.OptionMenu(
    root,
    selected_band_mode,
    "1 Octave",
    "1/3 Octave"
)
band_menu.pack(
    anchor="w",
    padx=30,
    pady=(0, 10)
)

new_trial_button = tk.Button(
    root,
    text="New Trial",
    command=create_trial
)
new_trial_button.pack(
    anchor="w",
    padx=30,
    pady=(5, 10)
)

#Line 3 of GUI

trial_label = tk.Label(
    root,
    text="Which sample contains the change in EQ?",
    font=("Arial", 14)
)
trial_label.pack(
    anchor="w",
    padx=30,
    pady=(20, 1)
)

trial_button_frame = tk.Frame(root)
trial_button_frame.pack(
    anchor="w",
    padx=30,
    pady=(0, 5)
)

sample_a_button = tk.Button(
    trial_button_frame,
    text="A"
)
sample_a_button.pack(side="left", padx=(0, 5))

sample_b_button = tk.Button(
    trial_button_frame,
    text="B"
)
sample_b_button.pack(side="left", padx=5)


root.mainloop()