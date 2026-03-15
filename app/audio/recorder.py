import sounddevice as sd
import soundfile as sf
import queue
import threading

class AudioRecorder:
    def __init__(self, filename, samplerate=44100, channels=1):
        self.filename = filename
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.q = queue.Queue()

    def callback(self, indata, frames, time, status):
        """This runs continuously in the background while recording."""
        if self.recording:
            self.q.put(indata.copy())

    def _write_file(self):
        """Continuously takes audio chunks from the queue and writes them to the file."""
        with sf.SoundFile(self.filename, mode='w', samplerate=self.samplerate, channels=self.channels) as file:
            while self.recording or not self.q.empty():
                try:
                    data = self.q.get(timeout=0.1)
                    file.write(data)
                except queue.Empty:
                    continue

    def start(self):
        """Starts the microphone stream and the background saving thread."""
        self.recording = True
        self.stream = sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self.callback)
        self.stream.start()
        
        # We save to the file in a separate thread so the UI never freezes!
        self.write_thread = threading.Thread(target=self._write_file)
        self.write_thread.start()

    def stop(self):
        """Stops recording and finalizes the audio file."""
        self.recording = False
        self.stream.stop()
        self.stream.close()
        self.write_thread.join()
        return self.filename