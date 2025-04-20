from fastapi import FastAPI, Form
from twilio.twiml.messaging_response import MessagingResponse
from pydantic import BaseModel
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

produtos = [
    {"id": "1", "nome": "Tênis Esportivo Branco", "descricao": "Tênis branco com detalhes azuis, ótimo para corrida.",
     "preco": 199.90, "imagem_url": "https://exemplo.com/tenis1.jpg"},
    {"id": "2", "nome": "Carregador Rápido Samsung", "descricao": "Carregador turbo 25W compatível com Samsung.",
     "preco": 89.90, "imagem_url": "https://exemplo.com/carregador.jpg"},
    {"id": "3", "nome": "Fone de Ouvido Bluetooth", "descricao": "Fone sem fio com cancelamento de ruído.",
     "preco": 149.90, "imagem_url": "https://exemplo.com/fone.jpg"},
]

TWILIO_PHONE_NUMBER = 'whatsapp:+14155238886'
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.post("/whatsapp/")
async def receber_whatsapp(mensagem: str = Form(...), from_number: str = Form(...)):
    texto = mensagem.lower()
    respostas = []

    for produto in produtos:
        if any(palavra in produto["descricao"].lower() or palavra in produto["nome"].lower() for palavra in texto.split()):
            respostas.append(f"{produto['nome']} - {produto['descricao']} - R${produto['preco']} - {produto['imagem_url']}")

    resposta = "Encontrei os seguintes produtos:\n" + "\n".join(respostas) if respostas else "Não encontrei nada com base na sua descrição."

    response = MessagingResponse()
    response.message(resposta)
    return str(response)
