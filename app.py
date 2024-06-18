
import streamlit as st
from extract_text import transcribe_audio
from process_text import process_text

# Title
st.title("Transcritor de Áudio")

# File Upload
uploaded_file = st.file_uploader("Escolha um arquivo de áudio...", type=["wav", "mp3", "m4a"])

if uploaded_file is not None:
    # Step 1: Extract text from the uploaded audio file
    st.write("Transcrevendo áudio...")
    transcribed_text = transcribe_audio(uploaded_file)
    st.write("Transcrição Completa!\nIniciando Processamento...")
    
    # Step 2: Process the extracted text using ChatGPT
    st.write("Processando o texto...")
    processed_text = process_text(transcribed_text)
    st.write("Análise Pronta: ")
    st.write(processed_text)

    # Step 3: Pasting the transcript
    st.write(transcribed_text)
