import time
from google_sheets import find_empty_cell, find_values, SPREADSHEET_ID, google_computer_engine
import streamlit as st
from extract_text import transcribe_audio
from process_text import process_text
from sqlalchemy import create_engine, text
import os

st.set_page_config(layout="wide")
# Title
st.write(st.secrets["GOOGLE_SETTINGS"]["type"])
st.title("Transcritor de Áudio")

# Customer guidelines
st.write("Grave sua consulta utilizando o gravador de áudio do celular ou de seu computador, e em seguida, abra-o abaixo.")


# File Upload
uploaded_file = st.file_uploader("Escolha um arquivo de áudio de até 25MB (versão beta)...", type=["wav", "mp3", "m4a"])

if uploaded_file is not None:
    
    # Step 1: Start the transcription process
    with st.spinner("Transcrevendo áudio..."):
        st.warning("A transcrição pode demorar um pouco.")
        start_time = time.time()
        transcribed_text = transcribe_audio(uploaded_file)
        end_time = time.time()
        actual_time = end_time - start_time

    # Step 2: Display timeout and completion message
    
    st.success("**Transcrição Completa!**", icon="✅")

    st.write(f"_Tempo de transcrição: {actual_time:.1f} segundos._")

    time.sleep(1)

    st.write("Iniciando Processamento...")    
    
    # Step 3: Process the extracted text using ChatGPT
    processed_text,improved_transcript = process_text(transcribed_text)
    st.write("**Texto Processado:**")
    st.write(processed_text) 
    ### There is a st.write_stream() function and a st.stream() function, try them later.

    # Step 4: Pasting the transcript
    st.write("**Transcrição Processada:**")
    st.write(improved_transcript)


    time.sleep(3)

    # Step 5: Get Feedback

st.write("**Como podemos melhorar?**")

feedback1 = [st.text_input(":blue[Deixe aqui seu feedback. Aperte [**enter**] para submeter.]",key="feedback")]

if st.session_state["feedback"] is not "":
    with st.spinner("Sending"):
        # Step 6: Connect google spreadsheet and get empty cell

        sheets = google_computer_engine()
        values = find_values(sheets)
        the_range = find_empty_cell(values)

        # Step 7: Insert the feedback into the spreadsheet
        body = {'values': [feedback1]}
        print(f'Body to update: {body}')

        try:
            response = sheets.values().update(
                spreadsheetId=SPREADSHEET_ID, 
                range=the_range, 
                valueInputOption='RAW', 
                body=body
            ).execute()
            
            print(f'Response: {response}')
        except Exception as e:
            print(f'Error: {e}')

        
        st.write(":green[Muito obrigado por usar o Transcritor!]")
        st.balloons()
