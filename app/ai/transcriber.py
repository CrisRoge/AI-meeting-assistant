import speech_recognition as sr
import os

def transcribe_audio(audio_file_path: str) -> str:
    """
    Takes a path to an audio file, sends it to the free Google Web Speech API,
    and returns the transcribed text. No API key required!
    """
    if not os.path.exists(audio_file_path):
        return "Audio file not found."

    recognizer = sr.Recognizer()
    
    try:
        # Load the saved .wav file
        with sr.AudioFile(audio_file_path) as source:
            print(f"Reading {audio_file_path}...")
            audio_data = recognizer.record(source)
            
            print("Sending to free Google Speech API...")
            # Use the free tier (recognize_google)
            text = recognizer.recognize_google(audio_data)
            
            print("Transcription complete.")
            return text

    except sr.UnknownValueError:
        return "The audio was unclear and could not be understood."
    except sr.RequestError as e:
        return f"Could not request results from Google Speech service; {e}"
    except Exception as e:
        return f"Error during transcription: {e}"