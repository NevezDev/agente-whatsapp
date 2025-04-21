import os
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from twilio.rest import Client
from dotenv import load_dotenv
import random
import string

load_dotenv()

app = FastAPI()

# Variáveis de ambiente
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(account_sid, auth_token)

# Dicionário de produtos (simulação)
produtos = {
    "camisa": {"preço": "R$ 50,00", "imagem_url": "https://dw0jruhdg6fis.cloudfront.net/producao/24866653/G/camisa_branca.jpg"},
    "celular": {"preço": "R$ 1200,00", "imagem_url": "https://samsungbrshop.vtexassets.com/arquivos/ids/228494/1000x1000_0000s_0047_SM-A155_Galaxy-A15-LTE_Blue-Black_Front2.jpg?v=638412055449170000"},
}

# Função para gerar um código de retirada
def gerar_codigo_retirada():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.post("/whatsapp/")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    print(f"Mensagem recebida de {From}: {Body}")

    if Body.lower() in produtos:
        produto = produtos[Body.lower()]
        imagem_url = produto["imagem_url"]
        preço = produto["preço"]

        # Enviar a resposta com detalhes do produto
        try:
            # Enviar detalhes do produto
            client.messages.create(
                body=f"Produto: {Body.capitalize()}\nPreço: {preço}\nClique na imagem para ver detalhes.",
                from_=twilio_number,
                to=From,
                media_url=[imagem_url],
            )

            # Gerar código de retirada
            codigo_retirada = gerar_codigo_retirada()

            # Confirmar o pedido e envio do código de retirada
            client.messages.create(
                body=f"Pedido confirmado! Seu código de retirada é: {codigo_retirada}",
                from_=f"whatsapp:{twilio_number}",
                to=From
            )
        except Exception as e:
            print("Erro ao enviar resposta:", str(e))

        return JSONResponse(content={"status": "Mensagem recebida e resposta enviada."})
    else:
        return JSONResponse(content={"status": "Produto não encontrado."})
