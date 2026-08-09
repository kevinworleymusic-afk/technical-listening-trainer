import numpy as np
import soundfile as sf
from scipy import signal


def create_modified_audio(frequency, gain_db, q=2):
    input_file = "Tracy_Chapman_Fast_car.wav"
    output_file = "modified.wav"

    audio, sample_rate = sf.read(input_file)

    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * frequency / sample_rate
    alpha = np.sin(w0) / (2 * q)

    b0 = 1 + alpha * A
    b1 = -2 * np.cos(w0)
    b2 = 1 - alpha * A

    a0 = 1 + alpha / A
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha / A

    b = np.array([b0, b1, b2]) / a0
    a = np.array([a0, a1, a2]) / a0

    # Filter Checks

    w, h = signal.freqz(b, a, worN=4096, fs=sample_rate)
    peak_index = np.argmax(np.abs(h))
    peak_frequency = w[peak_index]
    peak_gain_db = 20 * np.log10(np.abs(h[peak_index]))

    print("Peak frequency:", peak_frequency)
    print("Peak gain dB:", peak_gain_db)

    #End of Function
    modified = signal.lfilter(b, a, audio, axis=0)

    sf.write(output_file, modified, sample_rate)

    difference = np.max(np.abs(modified - audio))
    print("Maximum sample difference:", difference)

    print("Created:", output_file)

