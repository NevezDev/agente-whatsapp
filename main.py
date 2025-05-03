import os
import httpx
from fastapi import FastAPI, Request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

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

# Inicialização do FastAPI
app = FastAPI()

# Função para chamar o GPT-J da Hugging Face
async def gerar_resposta(prompt: str):
    url = "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-2.7B"
    headers = {
        "Authorization": f"Bearer {os.getenv('HF_API_KEY')}"
    }
    payload = {
        "inputs": prompt
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
    return response.json()

# Função para formatar resposta do chatbot
def gerar_mensagem_usuario(mensagem: str):
    return f"O que posso te ajudar com relação aos nossos produtos? Pergunte sobre nossos doces, bolos e tortas! Aqui estão alguns exemplos:\n{mensagem}"

# Função para enviar mensagem pelo Twilio
def enviar_mensagem_whatsapp(mensagem: str, destinatario: str):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_whatsapp = 'whatsapp:+14155238886'  # Número sandbox Twilio

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=mensagem,
        from_=from_whatsapp,
        to=f'whatsapp:{destinatario}'
    )
    return message.sid

# Endpoint que recebe as mensagens do WhatsApp via Twilio
@app.post("/whatsapp")
async def whatsapp(request: Request):
    form_data = await request.form()
    mensagem = form_data.get("Body")
    numero_usuario = form_data.get("From")

    # Verificar se a mensagem contém uma pergunta específica sobre produtos
    resposta = ""
    if "preço" in mensagem.lower() or "produto" in mensagem.lower():
        resposta = gerar_mensagem_usuario(mensagem)
    else:
        resposta = "Desculpe, não entendi a sua mensagem. Você pode perguntar sobre nossos produtos ou preços!"

    # Resposta do chatbot usando GPT-J
    response = await gerar_resposta(resposta)

    # Preparando a resposta final para o usuário
    resposta_chatbot = response[0]['generated_text'] if response else "Desculpe, ocorreu um erro."

    # Enviar a resposta para o WhatsApp via Twilio
    enviar_mensagem_whatsapp(resposta_chatbot, numero_usuario)

    # Retornar a resposta ao usuário via Twilio
    resp = MessagingResponse()
    resp.message(resposta_chatbot)
    return str(resp)

# Rota para testar localmente ou gerar resposta direta
@app.get("/testar")
async def testar():
    return {"mensagem": "API do chatbot está funcionando!"}
