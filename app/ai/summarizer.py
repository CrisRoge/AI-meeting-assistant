import os
import json
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY, SUMMARY_MODEL

def generate_meeting_summary(transcript_text: str):
    """Sends transcript to Gemini to extract a summary and action items."""
    
    # 1. Safety Checks
    if not GEMINI_API_KEY:
        print("Error: No API key found.")
        return {"short_summary": "Gemini API Key missing in .env file.", "decisions": "N/A"}

    if not transcript_text or "could not be understood" in transcript_text.lower():
        return {"short_summary": "Audio was too unclear to summarize.", "decisions": "N/A"}

    # 2. Initialize Gemini Client
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 3. Create the Prompt
    prompt = f"""
    Analyze the following meeting transcript. Provide a JSON response with exactly these two keys:
    1. "short_summary": A brief 2-3 sentence summary of the meeting.
    2. "decisions": A bulleted list of key decisions or action items.
    
    Transcript:
    {transcript_text}
    """
    
    # 4. Call the API
    try:
        print("Sending transcript to Gemini for summarization...")
        response = client.models.generate_content(
            model=SUMMARY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        print("Gemini summarization complete.")
        return json.loads(response.text)
        
    except Exception as e:
        print(f"Gemini Summarizer Error: {e}")
        return {
            "short_summary": f"Failed to generate summary: {e}", 
            "decisions": "Error connecting to Gemini."
        }