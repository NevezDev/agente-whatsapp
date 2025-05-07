from fastapi import FastAPI, Request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import requests
from data import produtos
from dotenv import load_dotenv
import uuid

load_dotenv()

app = FastAPI()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Dicionário para guardar pagamentos pendentes
pagamentos_pendentes = {}

def gerar_catalogo():
    catalogo = ""
    for p in produtos:
        catalogo += f"*{p['nome']}* - R${p['preco']:.2f}: {p['descricao']}\n{p['foto']}\n\n"
    return catalogo.strip()

def gerar_prompt(mensagem_cliente):
    catalogo = gerar_catalogo()
    return (
        f"Você é o AtendeBot, um atendente simpático de uma loja de doces. "
        f"Seu objetivo é ajudar os clientes a escolherem produtos e responder dúvidas com simpatia, mas sem dizer 'olá'. "
        f"Sempre inclua o link da imagem do produto em uma linha separada após a descrição.\n\n"
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

def gerar_pagamento_pix(nome_produto: str, valor: float):
    url = "https://api.mercadopago.com/v1/payments"
    idempotency_key = str(uuid.uuid4())

    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": idempotency_key
    }

    body = {
        "transaction_amount": valor,
        "description": f"Compra de {nome_produto}",
        "payment_method_id": "pix",
        "payer": {
            "email": "comprador@email.com"
        }
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 201:
        raise Exception(f"Erro ao gerar pagamento: {response.status_code} - {response.text}")

    data = response.json()
    return {
        "link": data["point_of_interaction"]["transaction_data"]["ticket_url"],
        "id": data["id"]
    }

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
                    pagamentos_pendentes[str(pagamento["id"])] = numero

                    resposta = (
                        f"✅ Pagamento gerado para *{produto['nome']}* no valor de R${produto['preco']:.2f}.\n\n"
                        f"Acesse o link para pagar via Pix:\n{pagamento['link']}"
                    )
                    imagem_url = produto["foto"]
                    break
            else:
                resposta = "❌ Desculpe, não encontrei esse produto para gerar o pagamento."
                imagem_url = None
        else:
            prompt = gerar_prompt(mensagem)
            resposta = enviar_pergunta_openrouter(prompt)

            # Extrai imagem da resposta
            linhas = resposta.splitlines()
            mensagem_sem_links = []
            imagem_url = None

            for linha in linhas:
                if linha.strip().startswith("http") and ("png" in linha or "jpg" in linha or "jpeg" in linha):
                    imagem_url = linha.strip()
                else:
                    mensagem_sem_links.append(linha)

            resposta = "\n".join(mensagem_sem_links).strip()

        # Envia a resposta via WhatsApp (com imagem se houver)
        if imagem_url:
            twilio_client.messages.create(
                body=resposta,
                from_="whatsapp:+14155238886",
                to=numero,
                media_url=[imagem_url]
            )
        else:
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

@app.post("/webhook")
async def webhook_mp(request: Request):
    body = await request.json()
    tipo_evento = body.get("action")
    dados = body.get("data", {})
    payment_id = str(dados.get("id"))

    if tipo_evento == "payment.updated" and payment_id:
        mp_url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {
            "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"
        }
        resposta = requests.get(mp_url, headers=headers)

        if resposta.status_code == 200:
            pagamento = resposta.json()
            status = pagamento.get("status")

            if status == "approved" and payment_id in pagamentos_pendentes:
                numero = pagamentos_pendentes.pop(payment_id)
                mensagem_confirmacao = "🎉 Pagamento confirmado! Seu pedido está sendo preparado com carinho. Obrigado! 🍬"

                try:
                    twilio_client.messages.create(
                        body=mensagem_confirmacao,
                        from_="whatsapp:+14155238886",
                        to=numero
                    )
                except Exception as e:
                    numero_sms = numero.replace("whatsapp:", "")
                    try:
                        twilio_client.messages.create(
                            body=mensagem_confirmacao,
                            from_="+14155238886",
                            to=numero_sms
                        )
                        print("Mensagem enviada por SMS como fallback.")
                    except Exception as sms_e:
                        print(f"Erro ao enviar SMS: {sms_e}")

    return {"status": "ok"}
