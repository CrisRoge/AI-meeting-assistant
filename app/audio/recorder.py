import sounddevice as sd
import soundfile as sf
import queue
import threading
import numpy as np

def get_audio_devices():
    """Scans for active devices using Windows WASAPI to filter out disabled/unplugged ones."""
    mics = []
    playbacks = []
    try:
        for i, dev in enumerate(sd.query_devices()):
            hostapi = sd.query_hostapis(dev['hostapi'])['name']
            
            # ENFORCE WASAPI: This guarantees we only see currently active/plugged-in devices!
            if 'WASAPI' in hostapi:
                name = dev['name']
                if dev['max_input_channels'] > 0:
                    mics.append({'id': i, 'name': f"🎤 {name}"})
                elif dev['max_output_channels'] > 0:
                    playbacks.append({'id': i, 'name': f"🔊 {name}"})
    except Exception as e:
        print(f"Device query error: {e}")
    return mics, playbacks

class AudioRecorder:
    def __init__(self, filename, mic_id=None, play_id=None, volume_callback=None):
        self.filename = filename
        self.mic_id = mic_id
        self.play_id = play_id
        self.recording = False
        self.q = queue.Queue()
        self.volume_callback = volume_callback
        
        # Standardize sample rate so Mic and Playback can be merged safely
        self.samplerate = 44100
        self.channels = 1
        
        self.stream_mic = None
        self.stream_play = None

    def callback(self, indata, frames, time, status):
        """Runs constantly in the background while recording."""
        if self.recording:
            # Convert incoming audio to Mono so both Mic and Playback can stack cleanly
            mono_data = np.mean(indata, axis=1, keepdims=True)
            self.q.put(mono_data.copy())
            
            if self.volume_callback:
                # Calculate the volume (RMS) to power the bouncing visualizer animation
                rms = np.sqrt(np.mean(mono_data**2))
                self.volume_callback(rms)

    def _write_file(self):
        with sf.SoundFile(self.filename, mode='w', samplerate=self.samplerate, channels=self.channels) as file:
            while self.recording or not self.q.empty():
                try:
                    data = self.q.get(timeout=0.1)
                    file.write(data)
                except queue.Empty:
                    continue

    def start(self):
        self.recording = True
        
        # 1. Start Microphone Stream safely
        if self.mic_id is not None:
            try:
                dev_info = sd.query_devices(self.mic_id)
                self.samplerate = int(dev_info['default_samplerate'])
                self.stream_mic = sd.InputStream(
                    device=self.mic_id, 
                    samplerate=self.samplerate, 
                    channels=max(1, dev_info['max_input_channels']), 
                    callback=self.callback
                )
                self.stream_mic.start()
            except Exception as e:
                print(f"Mic error: {e}")

        # 2. Start Playback Stream safely
        if self.play_id is not None:
            try:
                dev_info = sd.query_devices(self.play_id)
                if self.stream_mic is None:
                    # If no mic is selected, set the file sample rate to match the speakers
                    self.samplerate = int(dev_info['default_samplerate'])
                    
                self.stream_play = sd.InputStream(
                    device=self.play_id, 
                    samplerate=self.samplerate, 
                    channels=max(1, dev_info['max_output_channels']), 
                    callback=self.callback
                )
                self.stream_play.start()
            except Exception as e:
                print(f"Playback error: {e}")

        # 3. Start Saving to Disk
        self.write_thread = threading.Thread(target=self._write_file)
        self.write_thread.start()

    def stop(self):
        self.recording = False
        if self.stream_mic:
            self.stream_mic.stop()
            self.stream_mic.close()
        if self.stream_play:
            self.stream_play.stop()
            self.stream_play.close()
        if hasattr(self, 'write_thread'):
            self.write_thread.join()
        return self.filename