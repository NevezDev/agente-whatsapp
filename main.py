from fastapi import FastAPI, Request, BackgroundTasks
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import requests
from data import produtos
import json
from dotenv import load_dotenv
import uuid
import datetime

load_dotenv()

app = FastAPI()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

whatsapp_from = "whatsapp:+14155238886"
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Dicionários para guardar dados
pagamentos_pendentes = {}
CAMINHO_CLIENTES = "clientes.json"

# Adiciona campo de imagem aos produtos
for produto in produtos:
    produto["imagem"] = f"https://via.placeholder.com/300x300.png?text={produto['nome'].replace(' ', '+')}"

def salvar_cliente(numero):
    try:
        with open(CAMINHO_CLIENTES, "r") as f:
            clientes = json.load(f)
    except FileNotFoundError:
        clientes = []

    if numero not in clientes:
        clientes.append(numero)
        with open(CAMINHO_CLIENTES, "w") as f:
            json.dump(clientes, f)

def gerar_catalogo():
    catalogo = ""
    for p in produtos:
        catalogo += f"{p['nome']} - R${p['preco']:.2f}\n{p['descricao']}\nImagem: {p['imagem']}\n\n"
    return catalogo.strip()

def gerar_prompt(mensagem_cliente):
    catalogo = gerar_catalogo()
    return (
        f"Você é o AtendeBot, um atendente simpático de uma loja de doces. "
        f"Seu objetivo é ajudar os clientes a escolherem produtos e responder dúvidas com simpatia.\n\n"
        f"Catálogo:\n{catalogo}\n\n"
        f"Mensagem do cliente: {mensagem_cliente}\n"
        f"Responda de forma natural e útil. Se o cliente demonstrar interesse claro em pagar, apenas pergunte se ele deseja pagar via Pix."
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
        "payer": {"email": "comprador@email.com"}
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
        salvar_cliente(numero)

        for produto in produtos:
            if produto["nome"].lower() in mensagem:
                if any(palavra in mensagem for palavra in ["pagar", "comprar", "pix"]):
                    resposta = f"Você deseja realizar o pagamento de *{produto['nome']}* via Pix? (sim/não)"
                else:
                    resposta = f"{produto['nome']} custa R${produto['preco']:.2f}.\nDescrição: {produto['descricao']}\nImagem: {produto['imagem']}"
                break
        else:
            prompt = gerar_prompt(mensagem)
            resposta = enviar_pergunta_openrouter(prompt)

        twilio_client.messages.create(
            body=resposta,
            from_=whatsapp_from,
            to=numero
        )

    except Exception as e:
        erro = f"Erro ao processar: {e}"
        twilio_client.messages.create(
            body=erro,
            from_=whatsapp_from,
            to=numero
        )

    twiml = MessagingResponse()
    twiml.message("Processando sua mensagem...")
    return str(twiml)

@app.post("/responder_confirmacao")
async def confirmar_pagamento(request: Request):
    form = await request.form()
    mensagem = form.get("Body").lower()
    numero = form.get("From")

    if mensagem.startswith("sim"):
        for produto in produtos:
            if produto["nome"].lower() in mensagem:
                pagamento = gerar_pagamento_pix(produto["nome"], produto["preco"])
                pagamentos_pendentes[str(pagamento["id"])] = numero

                link = f"✅ Pagamento gerado para *{produto['nome']}* no valor de R${produto['preco']:.2f}.\n{pagamento['link']}"
                twilio_client.messages.create(body=link, from_=whatsapp_from, to=numero)
                break

    return "OK"

@app.post("/webhook")
async def webhook_mp(request: Request):
    body = await request.json()
    tipo_evento = body.get("action")
    dados = body.get("data", {})
    payment_id = str(dados.get("id"))

    if tipo_evento == "payment.updated" and payment_id:
        mp_url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
        resposta = requests.get(mp_url, headers=headers)

        if resposta.status_code == 200:
            pagamento = resposta.json()
            status = pagamento.get("status")

            if status == "approved" and payment_id in pagamentos_pendentes:
                numero = pagamentos_pendentes.pop(payment_id)
                mensagem = "🎉 Pagamento confirmado! Seu pedido está sendo preparado com carinho. Obrigado! 🍬"

                try:
                    twilio_client.messages.create(body=mensagem, from_=whatsapp_from, to=numero)
                except:
                    numero_sms = numero.replace("whatsapp:", "")
                    twilio_client.messages.create(body=mensagem, from_="+14155238886", to=numero_sms)

    return {"status": "ok"}

@app.get("/enviar-mensagens-semanais")
def enviar_mensagens_automaticamente():
    try:
        with open(CAMINHO_CLIENTES, "r") as f:
            clientes = json.load(f)

        mensagem = "🍬 Promoção da semana! Confira nossos doces incríveis com desconto!\n"
        for p in produtos:
            mensagem += f"\n{p['nome']} - R${p['preco']:.2f}\n{p['imagem']}"

        for cliente in clientes:
            twilio_client.messages.create(body=mensagem, from_=whatsapp_from, to=cliente)

        return {"status": "Mensagens enviadas"}
    except Exception as e:
        return {"erro": str(e)}
