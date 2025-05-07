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

# Carregamento de variáveis de ambiente
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

# Instância do cliente Twilio
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

CATALOGO_IMAGEM_URL = "https://marketplace.canva.com/EAF1LhAYvpE/2/0/900w/canva-card%C3%A1pio-bolo-doces-caseiros-moderno-rosa-instagram-story-qcdIFFP9PIw.jpg"
pagamentos_pendentes = {}

INSTRUCOES = "\n\n📌 Para ver a foto de algum produto, diga: 'ver foto do NOME_DO_PRODUTO' ou apenas o nome do produto.\n📌 Para pagar, diga: 'quero comprar NOME_DO_PRODUTO'."


def gerar_prompt(mensagem_cliente):
    catalogo_textual = ""
    for p in produtos:
        catalogo_textual += f"{p['nome']} - R${p['preco']:.2f}: {p['descricao']}\n"

    return (
        f"Você é o AtendeBot, um atendente simpático de uma loja de doces. "
        f"Seu objetivo é ajudar os clientes a escolherem produtos e responder dúvidas com simpatia.\n\n"
        f"Catálogo resumido:\n{catalogo_textual}\n\n"
        f"Mensagem do cliente: {mensagem_cliente}\n"
        f"Responda de forma natural e útil. "
        f"Se o cliente quiser pagar, diga: 'Pagamento iniciado para o produto NOME. Por favor, aguarde o link para pagamento.'"
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


def enviar_catalogo_imagem(numero):
    twilio_client.messages.create(
        body="🍬 Aqui está nosso catálogo! Veja todos os nossos doces disponíveis.\n\nCaso queira comprar algo, diga: 'quero comprar NOME_DO_PRODUTO'.\nSe quiser mais de um produto, digite todos os nomes juntos!",
        from_="whatsapp:+14155238886",
        to=numero,
        media_url=[CATALOGO_IMAGEM_URL]
    )


@app.post("/whatsapp")
async def responder_mensagem(request: Request):
    form = await request.form()
    mensagem = form.get("Body").lower()
    numero = form.get("From")

    try:
        if any(palavra in mensagem for palavra in ["catálogo", "produtos", "ver doces", "ver catálogo"]):
            enviar_catalogo_imagem(numero)
            return str(MessagingResponse())

        if any(palavra in mensagem for palavra in ["pagar", "quero comprar"]):
            produtos_encontrados = [p for p in produtos if p["nome"].lower() in mensagem]
            if not produtos_encontrados:
                twilio_client.messages.create(
                    body="❌ Desculpe, não encontrei os produtos mencionados." + INSTRUCOES,
                    from_="whatsapp:+14155238886",
                    to=numero
                )
                return str(MessagingResponse())

            total = sum(p["preco"] for p in produtos_encontrados)
            descricao = ", ".join(p["nome"] for p in produtos_encontrados)

            pagamento = gerar_pagamento_pix(descricao, total)
            pagamentos_pendentes[str(pagamento["id"])] = numero

            resposta = (
                f"✅ Pagamento gerado para: {descricao}\nTotal: R${total:.2f}\n\n"
                f"Acesse o link para pagar via Pix:\n{pagamento['link']}\n\nDeseja mais alguma coisa?"
            )
            twilio_client.messages.create(
                body=resposta,
                from_="whatsapp:+14155238886",
                to=numero
            )
            return str(MessagingResponse())

        if "ver foto" in mensagem or any(produto["nome"].lower() in mensagem for produto in produtos):
            for produto in produtos:
                if produto["nome"].lower() in mensagem:
                    twilio_client.messages.create(
                        body=f"📷 Aqui está a foto do {produto['nome']}!" + INSTRUCOES,
                        from_="whatsapp:+14155238886",
                        to=numero,
                        media_url=[produto["foto"]]
                    )
                    return str(MessagingResponse())

        if any(palavra in mensagem for palavra in ["não", "nada", "obrigado", "obrigada"]):
            twilio_client.messages.create(
                body="🙏 Agradecemos a preferência! Volte sempre que quiser mais docinhos! 🍭",
                from_="whatsapp:+14155238886",
                to=numero
            )
            return str(MessagingResponse())

        # IA responde normalmente
        prompt = gerar_prompt(mensagem)
        resposta = enviar_pergunta_openrouter(prompt)

        linhas = resposta.splitlines()
        mensagem_sem_links = []
        imagem_url = None
        for linha in linhas:
            if linha.strip().startswith("http") and ("png" in linha or "jpg" in linha or "jpeg" in linha):
                imagem_url = linha.strip()
            else:
                mensagem_sem_links.append(linha)

        resposta = "\n".join(mensagem_sem_links).strip() + INSTRUCOES

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
        erro = f"Erro ao processar: {e}" + INSTRUCOES
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
