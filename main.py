from fastapi import FastAPI, Request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import requests
from data import produtos

app = FastAPI()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def gerar_catalogo():
    catalogo = ""
    for p in produtos:
        catalogo += f"{p['nome']} - R${p['preco']:.2f}\n{p['descricao']}\n\n"
    return catalogo.strip()

def gerar_prompt(mensagem_cliente):
    catalogo = gerar_catalogo()
    return (
        f"Você é o AtendeBot, um atendente simpático de uma loja de doces. "
        f"Seu objetivo é ajudar os clientes a escolherem produtos e responder dúvidas com simpatia.\n\n"
        f"Catálogo:\n{catalogo}\n\n"
        f"Mensagem do cliente: {mensagem_cliente}\n"
        f"Responda de forma natural e útil."
    )

def enviar_pergunta_openrouter(mensagem):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "openchat/openchat-3.5",
        "messages": [
            {"role": "user", "content": mensagem}
        ]
    }

    response = requests.post(url, json=body, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Erro ao acessar OpenRouter: {response.status_code} - {response.text}")

@app.post("/whatsapp")
async def responder_mensagem(request: Request):
    form = await request.form()
    mensagem = form.get("Body")
    numero = form.get("From")

    try:
        prompt = gerar_prompt(mensagem)
        resposta = enviar_pergunta_openrouter(prompt)
    except Exception as e:
        resposta = f"Erro ao processar: {e}"

    twiml = MessagingResponse()
    twiml.message(resposta)
    return str(twiml)
