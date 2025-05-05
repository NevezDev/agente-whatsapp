from fastapi import FastAPI, Request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import requests
from data import produtos
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

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
        f"Seu objetivo é ajudar os clientes a escolherem produtos e responder dúvidas com simpatia, mas sem dizer 'olá'.\n\n"
        f"Catálogo:\n{catalogo}\n\n"
        f"Mensagem do cliente: {mensagem_cliente}\n"
        f"Responda de forma natural e útil. "
        f"Se o cliente desejar pagar, diga: 'Pagamento iniciado para o produto NOME. Por favor, aguarde o link para pagamento.'"
    )

def enviar_pergunta_openrouter(mensagem):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "opengvlab/internvl3-14b:free",
        "messages": [
            {"role": "user", "content": mensagem}
        ]
    }

    response = requests.post(url, json=body, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Erro ao acessar OpenRouter: {response.status_code} - {response.text}")

import uuid

def gerar_pagamento_pix(nome_produto: str, valor: float):
    url = "https://api.mercadopago.com/v1/payments"
    
    # Gerar um UUID único para a chave de idempotência
    idempotency_key = str(uuid.uuid4())  # Gera um valor único para a chave
    
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": idempotency_key  # Passando o UUID como chave
    }
    
    body = {
        "transaction_amount": valor,
        "description": f"Compra de {nome_produto}",
        "payment_method_id": "pix",
        "payer": {
            "email": "comprador@email.com"  # Pode ser genérico, obrigatório
        }
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 201:
        data = response.json()
        return {
            "link": data["point_of_interaction"]["transaction_data"]["ticket_url"],
            "qr_code": data["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        }
    else:
        raise Exception(f"Erro ao gerar pagamento: {response.status_code} - {response.text}")


@app.post("/whatsapp")
async def responder_mensagem(request: Request):
    form = await request.form()
    mensagem = form.get("Body").lower()
    numero = form.get("From")

    try:
        if "pagar" in mensagem or "quero comprar" in mensagem:
            for produto in produtos:
                if produto["nome"].lower() in mensagem:
                    pagamento = gerar_pagamento_pix(produto["nome"], produto["preco"])
                    resposta = (
                        f"✅ Pagamento gerado para *{produto['nome']}* no valor de R${produto['preco']:.2f}.\n\n"
                        f"Acesse o link para pagar via Pix:\n{pagamento['link']}"
                    )
                    break
            else:
                resposta = "❌ Desculpe, não encontrei esse produto para gerar o pagamento."
        else:
            prompt = gerar_prompt(mensagem)
            resposta = enviar_pergunta_openrouter(prompt)

        twilio_client.messages.create(
            body=resposta,
            from_="whatsapp:+14155238886",
            to=numero
        )

    except Exception as e:
        erro = f"Erro ao processar: {e}"
        twilio_client.messages.create(
            body=erro,
            from_="whatsapp:+14155238886",
            to=numero
        )

    twiml = MessagingResponse()
    twiml.message("Processando sua mensagem...")
    return str(twiml)
