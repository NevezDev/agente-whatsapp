import os
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from twilio.rest import Client
from dotenv import load_dotenv
import openai

load_dotenv()

app = FastAPI()

# 🔑 Variáveis de ambiente
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
openai_api_key = os.getenv("OPENAI_API_KEY")

client = Client(account_sid, auth_token)

openai.api_key = openai_api_key

# 📦 Banco de dados simulado de produtos
produtos = {
    "bolo de chocolate": {"preço": "R$ 35,00"},
    "bolo de cenoura": {"preço": "R$ 30,00"},
    "brigadeiro": {"preço": "R$ 3,00"},
    "beijinho": {"preço": "R$ 3,00"},
    "cajuzinho": {"preço": "R$ 3,00"},
    "torta de morango": {"preço": "R$ 45,00"},
    "torta de limão": {"preço": "R$ 40,00"},
    "pudim de leite": {"preço": "R$ 25,00"},
}

# 🤖 Função para gerar resposta usando o ChatGPT
def gerar_resposta_chatgpt(mensagem_usuario):
    prompt = f"""
Você é um atendente de uma loja de doces chamada AtendeBot.
Responda de forma educada, divertida e clara. Sugira produtos se o cliente pedir ajuda.
Base de produtos: {list(produtos.keys())}

Mensagem do cliente: "{mensagem_usuario}"
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um atendente de loja de doces."},
            {"role": "user", "content": prompt}
        ]
    )
    return resposta['choices'][0]['message']['content']

# 📩 Rota principal do webhook
@app.post("/whatsapp/")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    print(f"Mensagem recebida de {From}: {Body}")

    mensagem_usuario = Body.strip().lower()

    # Verificar se a mensagem corresponde a algum produto diretamente
    if mensagem_usuario in produtos:
        produto = produtos[mensagem_usuario]
        resposta = f"🍬 Produto: {mensagem_usuario.title()}\n💰 Preço: {produto['preço']}"

        # Enviar detalhes do produto
        client.messages.create(
            body=resposta,
            from_=twilio_number,
            to=From
        )
        return JSONResponse(content={"status": "Produto enviado!"})

    else:
        # Resposta gerada pelo ChatGPT
        resposta_chatgpt = gerar_resposta_chatgpt(Body)

        # Enviar resposta
        client.messages.create(
            body=resposta_chatgpt,
            from_=twilio_number,
            to=From
        )

        return JSONResponse(content={"status": "Resposta enviada pelo ChatGPT."})
