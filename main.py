# main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from twilio.rest import Client
import openai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configurações
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
openai_api_key = os.getenv("OPENAI_API_KEY")

client_twilio = Client(account_sid, auth_token)
openai.api_key = openai_api_key

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

# Função para buscar produto
def buscar_produto(nome_produto):
    for produto in produtos:
        if nome_produto.lower() in produto["nome"].lower():
            return produto
    return None

# Função para gerar resposta com ChatGPT
def gerar_resposta_chatgpt(mensagem_usuario):
    prompt = f"""
Você é um atendente de uma loja de doces chamada AtendeBot.

Produtos disponíveis:
{formatar_produtos_para_prompt()}

Quando o cliente perguntar sobre produtos ou fazer perguntas, responda de forma natural e amigável.
Se ele pedir algum doce específico, dê uma pequena descrição e preço.

Mensagem do cliente: {mensagem_usuario}
"""
    resposta = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um assistente de vendas de uma loja de doces."},
            {"role": "user", "content": prompt}
        ]
    )
    return resposta.choices[0].message.content.strip()

def formatar_produtos_para_prompt():
    texto = ""
    for p in produtos:
        texto += f"- {p['nome']} ({p['categoria']}): {p['descricao']} - R${p['preco']:.2f}\n"
    return texto

# Rota principal
@app.post("/whatsapp/")
async def whatsapp_webhook(request: Request):
    data = await request.form()
    mensagem_usuario = data.get("Body")
    From = data.get("From")

    if not mensagem_usuario:
        return JSONResponse(content={"status": "Mensagem vazia."})

    resposta = gerar_resposta_chatgpt(mensagem_usuario)

    # Enviar a resposta via WhatsApp
    client_twilio.messages.create(
        body=resposta,
        from_=twilio_number,
        to=From
    )

    return JSONResponse(content={"status": "Mensagem enviada!"})
