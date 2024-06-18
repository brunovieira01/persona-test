from openai import OpenAI
import openai
import os

API_KEY=os.environ['OPENAI_API_KEY']
print(API_KEY)
openai.api_key = API_KEY
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])



def process_text(text):

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
              "content": (
                  """Você é um ajudante para médicos, e vai organizar os dados de
                    uma consulta.\n Extraia todas as informações básicas do paciente,
                      e crie um segmento (estilo markdown) para mostrar estas 
                      informações, como a seguir:\n(entenda cada \n como um line break)
                      Nome: Alberto Marinho\n Idade: 39 anos\n Gênero: Masculino\n
                      Contato: ...\n\n Em seguida, crie outro segmento para 
                      a história médica, e depois um para Sintomas e Razão Para Visita.
                      Caso não encontres alguma informação, coloque o campo vazio,
                      desse jeito: Gênero:           \n"""
                )
            },
            {"role": "user", "content": f"{text}"}],
        stream=False,
    )
    content = response.choices[0].message.content
    return content