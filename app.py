import time
import numpy as np
import streamlit as st
from extract_text import transcribe_audio
from process_text import process_text
from sqlalchemy import create_engine, text
import os

st.set_page_config(layout="wide")
# Title
st.title("Transcritor de Áudio")

if os.environ["OPENAI_API_KEY"] != st.secrets["OPENAI_API_KEY"]:
    raise st.write(":grey[Environment Variables Don't Match!]",)

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
    
    st.balloons()


    # Step 5: Get Feedback

    st.write("**Como podemos melhorar?**")

    feedback1 = st.text_input(":blue[Deixe aqui seu feedback.]")

    # if feedback1 is not ":red[Deixe aqui seu feedback.]":

    #     time.sleep(2)
    #     # Step 6: Create the SQL connection as specified in your secrets file.
    #     conn = st.connection('fb_db', type='sql')

    #     st.write(f"conn contents: {conn}")

    #     # Step 7: Insert some data with conn.session.
    #     with conn.session as s:
    #         s.execute(text('CREATE TABLE IF NOT EXISTS feedback (Sobre_Você TEXT, Feedback TEXT);'))
    #         people = {'Bruno': 'Sou estudante de administração'}
    #         for k in people:
    #             s.execute(text(
    #                 'INSERT INTO people (Sobre_Você,Feedback) VALUES (:name, :feed);'),
    #                 params=dict(name=k, feed=people[k])
    #             )
    #         s.commit()

    #     # Step 8: Query and display the data you inserted
    #     feedback0 = conn.query('select * from feedback')
    #     st.dataframe(feedback0)