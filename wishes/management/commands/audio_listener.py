import os
import time
import random
import uuid
import subprocess
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
from datetime import datetime
from collections import deque
from scipy.signal import butter, lfilter
from ...consumers import WishConsumer
#modell
from wishes.models import Wish
from ...signals import push_wish_update
#basecommand
from django.core.management.base import BaseCommand

#Grundlegende Einstellungen
SAMPLE_RATE = 44100
THRESHOLD = 20.0#Lautstärken threshold
RECORD_AFTER_TRIGGER = 4.0 # Sekunden nach dem trigger
CHUNK_DURATION = 0.2  # Sek.
CHUNK_SIZE = 1024
BUFFER_SECONDS = 1
VOICE_FREQUENCY_RANGE = (85, 300)  # Frequenzen der menschlichen Stimme
MESSING_FREQUENCY_RANGE = (3000, 20000)  # Frequenzen für Messingplatten
MEDIA_ROOT = "media/"

COLORS = ["#3D314A", "#EEB160", "#E4E381", "#B9C4DE"]


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

            audio_chunk = indata[:, 0]  # Nur Mono aufnehmen
            ringbuffer.extend(audio_chunk)  # Füge den aktuellen Audio-Chunk zum Ringbuffer hinzu



             # Stimmen herausfiltern (Frequenzen zwischen 85 Hz und 300 Hz dämpfen)
            audio_chunk_no_voices = bandpass_filter(audio_chunk, VOICE_FREQUENCY_RANGE[0], VOICE_FREQUENCY_RANGE[1], SAMPLE_RATE)

            # Frequenzanalyse: FFT anwenden, um die dominante Frequenz zu bestimmen
            fft_data = np.fft.fft(audio_chunk_no_voices)
            freqs = np.fft.fftfreq(len(fft_data), 1 / SAMPLE_RATE)
            magnitude = np.abs(fft_data)

            peak_freq = freqs[np.argmax(magnitude)]  # Dominante Frequenz ermitteln
            #print(f"Erkannte Frequenz: {peak_freq} Hz")

            volume = np.linalg.norm(audio_chunk) * 10  # Berechne die Lautstärke des Chunks
            
            if MESSING_FREQUENCY_RANGE[0] <= peak_freq <= MESSING_FREQUENCY_RANGE[1] :
                print(f"lautstärke {volume}, frequenz {peak_freq}")
                
                if volume > THRESHOLD:
                    
                    print("--------Trigger durch Messingplatte erkannt!-----")

                    if not triggered:
                        triggered = True
                        post_recording = []  # Setze die Nachaufnahme zurück

            

            if triggered:
                post_recording.extend(audio_chunk)  # Wenn bereits getriggert, speichere den Chunk in der Nachaufnahme
                if len(post_recording) >= after_trigger_frames:
                    save_recording()  # Nachträgliche Aufnahme speichern
                    triggered = False  # Stoppe die Aufnahme
                    post_recording = []  # Leere die Nachaufnahme


       
        def save_recording():
           
            
            full = np.array(post_recording, dtype=np.float32)
           

            # In 16bit WAV konvertieren
            full_int16 = (full * 32767).astype(np.int16)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            wav_name = f"{timestamp}_{uuid.uuid4().hex}.wav"
            wav_path = os.path.join(MEDIA_ROOT, wav_name)
            

            # WAV-Datei speichern
            wav.write(wav_path, SAMPLE_RATE, full_int16)
            
            model_color = COLORS[random.randint(0,3)]

            #Modell speichern
            Wish.objects.create(
                sound = wav_path,
                color = model_color,
                pub_date = datetime.now().strftime("%Y%m%d_%H%M%S")
                )
             # Pause
            time.sleep(2.0)  # Pause

        print("start audio stream")

        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE, callback=audio_callback):
            while True:
                time.sleep(0.1)  # Pause


