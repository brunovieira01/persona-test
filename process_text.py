from openai import OpenAI
import openai
import os
import streamlit as st

OPENAI = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key = OPENAI)



def process_text(text):

    #1 Improve Transcription

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
              "content": ("""Essa é uma transcrição de um áudio. Com o mínimo de 
                          mudanças necessário, verifique se há constância das regras
                           gramaticais, ajustando o texto conforme necessário. Quero
                           também que verifique o contexto, e caso encontre palavras 
                          que soem similares mas que uma delas não faz sentido, mude-a
                           para manter o contexto. Lembre-se que há um médico 
                          perguntando e um paciente (ou mais) respondendo. Mas repito,
                           só faça isso quando tiver muita segurança, como no exemplo 
                          a seguir: 'Para dor de cabeça, recomendo para se ta mole.'->
                           'Para dor de cabeça, recomendo paracetamol.' Caso contrário,
                          não mude nada. Essa é uma tarefa delicada, então vá devagar
                          e passo a passo."""
                )
            },
            {"role": "user", "content": f"{text}"}],
        stream=False,
    )
    improved_transcription = response.choices[0].message.content

    #2 Process the transcription

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
              "content": (
                  """Você é um ajudante para médicos, e vai organizar os dados de
                    uma consulta. Extraia todas as informações básicas do paciente,
                      e crie um segmento (estilo markdown) para mostrar estas 
                      informações, como a seguir:(entenda cada como um line break)
                      Nome: Alberto Marinho\n Idade: 39 anos\n Gênero: Masculino\n
                      Contato: ...\n\n Em seguida, crie outro segmento para 
                      a história médica, e depois um para Sintomas e Razão Para Visita.
                      Caso não encontre alguma informação, coloque o campo vazio. 
                      Dê mais ênfase para as informações que o médico fala quando
                      encontrar dados conflitantes."""
                )
            },
            {"role": "user", "content": f"{improved_transcription}",}],
        stream=False,
    )
    content = response.choices[0].message.content

    return content, improved_transcription