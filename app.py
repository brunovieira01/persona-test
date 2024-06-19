import time
import streamlit as st
from extract_text import transcribe_audio
from process_text import process_text

# Title
st.title("Transcritor de Áudio")

# Customer guidelines
st.write("Grave sua consulta utilizando o gravador de áudio do celular ou de seu computador, e em seguida, abra-o abaixo.")


# File Upload
uploaded_file = st.file_uploader("Escolha um arquivo de áudio...", type=["wav", "mp3", "m4a"])

if uploaded_file is not None:
    
    # Step 1: Start the transcription process
    with st.spinner("Transcrevendo áudio..."):
        st.warning("A transcrição pode demorar um pouco.")
        start_time = time.time()
        transcribed_text = transcribe_audio(uploaded_file)
        end_time = time.time()
        actual_time = end_time - start_time

    # Step 2: Display timeout and completion message
    
    st.write("Transcrição Completa!\nIniciando Processamento...")

    st.write(f"Tempo real de transcrição: {actual_time:.2f} segundos.")
    
    
    # Step 3: Process the extracted text using ChatGPT
    st.write("Processando o texto...")
    processed_text,improved_transcript = process_text(transcribed_text)
    st.write("*Análise Pronta:* ")
    st.write(processed_text)

    # Step 4: Pasting the transcript
    st.write("\n\n\n\nTranscrição Processada:")
    st.write(improved_transcript)


    # Step 5: Feedback
    st.write("Como podemos melhorar?\n\n\n")

    feedback = st.chat_input("Deixe aqui seu feedback.")

    feedback1 = st.text_input("Deixe aqui seu feedback.")

    