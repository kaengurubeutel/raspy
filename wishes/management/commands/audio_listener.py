import os
import time
import random
import uuid
import subprocess
from threading import Thread
from queue import Queue
import numpy as np
import scipy.io.wavfile as wav
import pygame
import sounddevice as sd
from datetime import datetime
from collections import deque
from scipy.signal import butter, lfilter
from django.core.management.base import BaseCommand
from wishes.models import Wish

# Grundlegende Einstellungen
SAMPLE_RATE = 44100
THRESHOLD = 20.0  # Lautstärken-Threshold
RECORD_AFTER_TRIGGER = 4.0  # Sekunden nach Trigger
CHUNK_SIZE = 1024
BUFFER_SECONDS = 1
VOICE_FREQ_RANGE = (85, 300)
MESSING_FREQ_RANGE = (3000, 20000)
MEDIA_ROOT = "media/"
COLORS = ["#3D314A", "#EEB160", "#E4E381", "#B9C4DE"]

# Audio-Geräte festlegen
sd.default.device = ("Scarlett 8i6 USB: Audio (hw:2,0)",
                     "bluez_output.40_C1_F6_33_FA_83.1")

# Queue und Worker für Playback
play_queue = Queue()
def player_worker():
    while True:
        mp3 = play_queue.get()
        if mp3 is None:
            break
        # Direct playback via paplay
        subprocess.run(["paplay", "--device=bluez_output.40_C1_F6_33_FA_83.1", mp3])
        play_queue.task_done()
Thread(target=player_worker, daemon=True).start()

# Hilfsfunktionen

def butter_bandstop(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    return butter(order, [low, high], btype='bandstop')


def bandpass_filter(data, lowcut, highcut, fs):
    b, a = butter_bandstop(lowcut, highcut, fs)
    return lfilter(b, a, data)

class Command(BaseCommand):
    help = "Audio Listener with buffer"

    def handle(self, *args, **kwargs):
        os.makedirs(MEDIA_ROOT, exist_ok=True)
        ringbuffer = deque(maxlen=int(SAMPLE_RATE * BUFFER_SECONDS))
        triggered = False
        after_frames = int(SAMPLE_RATE * RECORD_AFTER_TRIGGER)
        post = []

        def audio_callback(indata, frames, time_info, status):
            nonlocal triggered, post
            if status:
                print("⚠️", status)
            try:
                chunk = indata[:, 0]
                ringbuffer.extend(chunk)
                filtered = bandpass_filter(chunk, *VOICE_FREQ_RANGE, SAMPLE_RATE)
                fft = np.fft.fft(filtered)
                freqs = np.fft.fftfreq(len(fft), 1/SAMPLE_RATE)
                peak = freqs[np.argmax(np.abs(fft))]
                volume = np.linalg.norm(chunk) * 10
                if MESSING_FREQ_RANGE[0] <= peak <= MESSING_FREQ_RANGE[1] and volume > THRESHOLD:
                    if not triggered:
                        triggered = True
                        post = []
                if triggered:
                    post.extend(chunk)
                    if len(post) >= after_frames:
                        save_recording(post.copy())
                        triggered = False
                        post = []
            except Exception as e:
                print("Callback Error:", e)

        def save_recording(frames_data):
            try:
                full = np.array(frames_data, dtype=np.float32)
                full_int16 = (full * 32767).astype(np.int16)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                wav_name = f"{ts}_{uuid.uuid4().hex}.wav"
                wav_path = os.path.join(MEDIA_ROOT, wav_name)
                wav.write(wav_path, SAMPLE_RATE, full_int16)

                color = random.choice(COLORS)
                newwish = Wish.objects.create(sound=wav_path, color=color, pub_date=ts)
                mp3_file = f"wishes/management/commands/numbersounds/MCBW_{newwish.id:04}.mp3"
                play_queue.put(mp3_file)
            except Exception as e:
                print("Save Error:", e)

        print("Start Audio Stream")
        try:
            with sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                                blocksize=CHUNK_SIZE,
                                callback=audio_callback):
                while True:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("Interrupted by user")
        except Exception as e:
            print("Stream Error:", e)
        finally:
            play_queue.put(None)  # Stop Worker
