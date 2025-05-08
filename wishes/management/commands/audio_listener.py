import os
import time
import random
import uuid
import subprocess
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import pygame
from datetime import datetime
from collections import deque
from scipy.signal import butter, lfilter
from ...consumers import WishConsumer
from wishes.models import Wish
from ...signals import push_wish_update
from django.core.management.base import BaseCommand

SAMPLE_RATE = 44100
THRESHOLD = 20.0
RECORD_AFTER_TRIGGER = 4.0
CHUNK_DURATION = 0.2
CHUNK_SIZE = 1024
BUFFER_SECONDS = 1
VOICE_FREQUENCY_RANGE = (85, 300)
MESSING_FREQUENCY_RANGE = (3000, 20000)
MEDIA_ROOT = "media/"
COLORS = ["#3D314A", "#EEB160", "#E4E381", "#B9C4DE"]

def play_mp3(mp3_file):
    if not os.path.exists(mp3_file):
        print(f"❌ Datei nicht gefunden: {mp3_file}")
        return
    try:
        os.environ["SDL_AUDIODRIVER"] = "pulseaudio"
        os.environ["PULSE_SINK"] = "bluez_output.40_C1_F6_33_FA_83.1"
        pygame.mixer.init()
        pygame.mixer.music.load(mp3_file)
        pygame.mixer.music.play()
        print(f"▶️ Wiedergabe: {mp3_file}")
        while pygame.mixer.music.get_busy():
            time.sleep(0.5)
    except Exception as e:
        print(f"❌ Fehler bei der Wiedergabe: {e}")

class Command(BaseCommand):
    help = "Audio Listener with buffer"

    def handle(self, *args, **kwargs):
        os.makedirs(MEDIA_ROOT, exist_ok=True)

        ringbuffer = deque(maxlen=int(SAMPLE_RATE * BUFFER_SECONDS))
        triggered = False
        after_trigger_frames = int(SAMPLE_RATE * RECORD_AFTER_TRIGGER)
        post_recording = []

        def butter_bandstop(lowcut, highcut, fs, order=4):
            nyquist = 0.5 * fs
            low = lowcut / nyquist
            high = highcut / nyquist
            b, a = butter(order, [low, high], btype='bandstop')
            return b, a

        def bandpass_filter(data, lowcut, highcut, fs, order=4):
            b, a = butter_bandstop(lowcut, highcut, fs, order)
            return lfilter(b, a, data)

        def audio_callback(indata, frames, time_info, status):
            nonlocal triggered, post_recording

            if status:
                print("⚠️", status)

            audio_chunk = indata[:, 0]
            ringbuffer.extend(audio_chunk)

            audio_chunk_no_voices = bandpass_filter(audio_chunk, VOICE_FREQUENCY_RANGE[0], VOICE_FREQUENCY_RANGE[1], SAMPLE_RATE)
            fft_data = np.fft.fft(audio_chunk_no_voices)
            freqs = np.fft.fftfreq(len(fft_data), 1 / SAMPLE_RATE)
            magnitude = np.abs(fft_data)
            peak_freq = freqs[np.argmax(magnitude)]
            volume = np.linalg.norm(audio_chunk) * 10

            if MESSING_FREQUENCY_RANGE[0] <= peak_freq <= MESSING_FREQUENCY_RANGE[1]:
                print(f"🔊 Lautstärke {volume:.2f}, Frequenz {peak_freq:.1f} Hz")
                if volume > THRESHOLD and not triggered:
                    print("✅ Trigger durch Messingplatte erkannt!")
                    triggered = True
                    post_recording = []

            if triggered:
                post_recording.extend(audio_chunk)
                if len(post_recording) >= after_trigger_frames:
                    save_recording()
                    triggered = False
                    post_recording = []

        def save_recording():
            full = np.array(post_recording, dtype=np.float32)
            full_int16 = (full * 32767).astype(np.int16)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            wav_name = f"{timestamp}_{uuid.uuid4().hex}.wav"
            wav_path = os.path.join(MEDIA_ROOT, wav_name)
            wav.write(wav_path, SAMPLE_RATE, full_int16)

            model_color = random.choice(COLORS)
            newwish = Wish.objects.create(
                sound=wav_path,
                color=model_color,
                pub_date=timestamp
            )

            number = newwish.id
            play_mp3(f"wishes/management/commands/numbersounds/MCBW_{number:04}.mp3")
            time.sleep(2.0)

        print("🎤 Starte Audio-Stream mit Scarlett 8i6 USB...")

        # Optional zur Device-Kontrolle:
        # print(sd.query_devices())

        # Nutze Scarlett explizit als Input
        input_device_name = "Scarlett 8i6 USB"
        with sd.InputStream(device=input_device_name, channels=1, samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE, callback=audio_callback):
            while True:
                time.sleep(0.1)
