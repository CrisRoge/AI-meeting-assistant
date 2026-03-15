import sounddevice as sd
import soundfile as sf
import queue
import threading
import numpy as np

def get_audio_devices():
    """Scans for valid audio inputs using the most stable Windows driver."""
    devices = []
    try:
        # Using the default Host API (MME) prevents the WASAPI silence bug
        default_api = sd.default.hostapi
        for i, dev in enumerate(sd.query_devices()):
            if dev['hostapi'] == default_api and dev['max_input_channels'] > 0:
                name = dev['name']
                # Hide the redundant Windows generic mappers to keep the list clean
                if "Sound Mapper" not in name:
                    devices.append({'id': i, 'name': f"🎙️ {name}"})
    except Exception as e:
        print(f"Device query error: {e}")
    return devices

class AudioRecorder:
    def __init__(self, filename, device_id=None, volume_callback=None):
        self.filename = filename
        self.device_id = device_id
        self.recording = False
        self.q = queue.Queue()
        self.volume_callback = volume_callback
        self.samplerate = 44100

    def callback(self, indata, frames, time, status):
        """Runs constantly in the background while recording."""
        if self.recording:
            self.q.put(indata.copy())
            
            if self.volume_callback:
                # Calculate the Root Mean Square (RMS) volume to power the animation
                rms = np.sqrt(np.mean(indata**2))
                self.volume_callback(rms)

    def _write_file(self):
        with sf.SoundFile(self.filename, mode='w', samplerate=int(self.samplerate), channels=1) as file:
            while self.recording or not self.q.empty():
                try:
                    data = self.q.get(timeout=0.1)
                    file.write(data)
                except queue.Empty:
                    continue

    def start(self):
        self.recording = True
        
        # Safely fetch the sample rate, but let Windows force it into Mono (1 channel)
        if self.device_id is not None:
            dev_info = sd.query_devices(self.device_id)
            self.samplerate = int(dev_info['default_samplerate'])

        self.stream = sd.InputStream(
            device=self.device_id, 
            samplerate=self.samplerate, 
            channels=1, # Letting Windows OS downmix to Mono is 100x safer!
            callback=self.callback
        )
        self.stream.start()
        
        self.write_thread = threading.Thread(target=self._write_file)
        self.write_thread.start()

    def stop(self):
        self.recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        if hasattr(self, 'write_thread'):
            self.write_thread.join()
        return self.filename