import os
from twilio.rest import Client
from fastapi import FastAPI, Request
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

app = FastAPI()

# Carregar variáveis de ambiente
load_dotenv()

# Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Base de dados de produtos
produtos = [
    {"nome": "Bolo de Chocolate", "categoria": "Bolos", "descricao": "Delicioso bolo de chocolate com cobertura cremosa.", "preco": 25.00},
    {"nome": "Brigadeiro Gourmet", "categoria": "Doces", "descricao": "Brigadeiros gourmet feitos com chocolate belga.", "preco": 2.50},
    {"nome": "Cupcake de Morango", "categoria": "Bolos", "descricao": "Cupcakes fofinhos com cobertura de morango natural.", "preco": 5.00},
    {"nome": "Beijinho", "categoria": "Doces", "descricao": "Tradicional beijinho de coco.", "preco": 2.00},
    {"nome": "Torta de Limão", "categoria": "Tortas", "descricao": "Torta de limão com base crocante e recheio cremoso.", "preco": 30.00},
    {"nome": "Bolo de Cenoura", "categoria": "Bolos", "descricao": "Bolo de cenoura com cobertura de chocolate.", "preco": 20.00},
    {"nome": "Cajuzinho", "categoria": "Doces", "descricao": "Doce tradicional de amendoim em formato de caju.", "preco": 2.00},
]

# Modelo de pedido do usuário
class ChatRequest(BaseModel):
    message: str
    from_number: str

@app.post("/whatsapp")
async def whatsapp(request: Request):
    data = await request.json()
    from_number = data['From']
    user_msg = data['Body'].strip()

    # Resposta sobre produtos
    if "produtos" in user_msg.lower() or "doces" in user_msg.lower() or "bolos" in user_msg.lower():
        categorias = set([produto["categoria"] for produto in produtos])
        response = "Temos os seguintes produtos por categoria:\n"
        
        for categoria in categorias:
            response += f"\nCategoria: {categoria}\n"
            for produto in produtos:
                if produto["categoria"] == categoria:
                    response += f"- {produto['nome']} (R${produto['preco']}) - {produto['descricao']}\n"
        return await send_whatsapp_message(from_number, response)

    # Usando OpenRouter para resposta natural
    bot_reply = await ask_openrouter(user_msg)
    return await send_whatsapp_message(from_number, bot_reply)


async def send_whatsapp_message(to_number: str, body: str):
    message = client.messages.create(
        body=body,
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        to=f"whatsapp:{to_number}"
    )
    return {"message_sid": message.sid}

# Função para comunicação com OpenRouter
async def ask_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=body, headers=headers)
        data = response.json()
        return data["choices"][0]["message"]["content"]
