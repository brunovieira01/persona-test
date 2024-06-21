import whisper
import os
from io import BytesIO
import numpy as np
import tempfile
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def transcribe_audio(uploaded_file): #ajuste para +25MB
    
    transcription = client.audio.transcriptions.create(
    model="whisper-1", 
    file=uploaded_file,  
    response_format="text"
    )

    return transcription

# The alternative below runs locally instead for cost effectiveness.

# def transcribe_audio(uploaded_file):
#     # Load Whisper model with FP32 precision on CPU
#     model = whisper.load_model("small", device="cpu")  # Try using a larger model if available

#     # Create a temporary file
#     with tempfile.NamedTemporaryFile(delete=False) as temp_audio_file:
#         temp_audio_file.write(uploaded_file.getbuffer())
#         temp_audio_file_path = temp_audio_file.name

#     # Use Whisper's utility to load audio data
#     audio = whisper.load_audio(temp_audio_file_path, sr=16000)   

#     # Convert to FP32 if necessary
#     audio = np.float32(audio)

#     # Normalize the audio
#     peak = np.abs(audio).max()
#     if peak > 0:
#         audio = audio / peak

#     # Check for NaN values in the audio data before processing
#     if np.isnan(audio).any():
#         raise ValueError("Audio data contains NaN values even after processing. Please check the input file.")

#     # Improved transcription with more robust settings
#     result = model.transcribe(audio, beam_size=5, best_of=5)

#     return result['text']
