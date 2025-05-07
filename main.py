from fastapi import FastAPI, Request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import requests
from data import produtos, horario_funcionamento
from dotenv import load_dotenv
import uuid
import re

load_dotenv()

app = FastAPI()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

CATALOGO_IMG_URL = "https://marketplace.canva.com/EAF1LhAYvpE/2/0/900w/canva-card%C3%A1pio-bolo-doces-caseiros-moderno-rosa-instagram-story-qcdIFFP9PIw.jpg"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

pagamentos_pendentes = {}
contexto_pos_pagamento = {}
enderecos_clientes = {}

NUMERO_DONO = "whatsapp:+5575998766261"

def extrair_pedidos(mensagem):
    pedidos = []
    for produto in produtos:
        if produto["nome"] in mensagem:
            match = re.search(r"(\d+)\s*(?:x\s*)?" + re.escape(produto["nome"]), mensagem)
            quantidade = int(match.group(1)) if match else 1
            pedidos.append((produto, quantidade))
    return pedidos

def gerar_pagamento_pix_pedido(pedidos):
    total = sum(produto["preco"] * qtd for produto, qtd in pedidos)
    descricao = ", ".join([f"{qtd}x {p['nome']}" for p, qtd in pedidos])
    body = {
        "transaction_amount": total,
        "description": f"Compra de doces: {descricao}",
        "payment_method_id": "pix",
        "payer": {
            "email": f"comprador{uuid.uuid4().hex[:6]}@exemplo.com"
        }
    }
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    resposta = requests.post("https://api.mercadopago.com/v1/payments", json=body, headers=headers)
    if resposta.status_code == 201:
        dados = resposta.json()
        return {
            "id": dados["id"],
            "link": dados["point_of_interaction"]["transaction_data"]["ticket_url"],
            "total": total
        }
    else:
        raise Exception("Erro ao gerar pagamento")

def enviar_pergunta_openrouter(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openchat/openchat-3.5",
        "messages": [
            {"role": "system", "content": "Você é um assistente de vendas simpático de uma loja de doces."},
            {"role": "user", "content": prompt}
        ]
    }
    resposta = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if resposta.status_code == 200:
        return resposta.json()["choices"][0]["message"]["content"]
    else:
        return "Desculpe, algo deu errado com a IA. Tente novamente mais tarde."

@app.post("/whatsapp")
async def responder_mensagem(request: Request):
    form = await request.form()
    mensagem = form.get("Body").lower()
    numero = form.get("From")

    try:
        if any(p in mensagem for p in ["horário", "funcionamento", "que horas", "abre", "fecha"]):
            horario = "\n".join([f"{dia}: {horas}" for dia, horas in horario_funcionamento.items()])
            resposta = f"🕒 Nosso horário de funcionamento:\n{horario}"

        elif any(p in mensagem for p in ["quero comprar", "comprar"]):
            pedidos = extrair_pedidos(mensagem)
            if pedidos:
                pagamento = gerar_pagamento_pix_pedido(pedidos)
                pagamentos_pendentes[str(pagamento["id"])] = numero
                lista_itens = "\n".join([f"{qtd}x {p['nome']} (R${p['preco']:.2f})" for p, qtd in pedidos])
                resposta = (
                    f"🧾 Pedido confirmado:\n{lista_itens}\n\n"
                    f"💰 Total: R${pagamento['total']:.2f}\n"
                    f"Clique para pagar via Pix:\n{pagamento['link']}"
                )
            else:
                resposta = "❌ Não encontrei os produtos mencionados no nosso catálogo. Por favor, verifique os nomes."

        elif any(p in mensagem for p in ["quero ver", "ver cardápio", "ver catálogo", "sim", "desejo"]):
            twilio_client.messages.create(
                media_url=[CATALOGO_IMG_URL],
                body="Aqui está o nosso cardápio! 🍰🍬\n\nO que você gostaria de pedir?\n\nPara fazer um pedido, diga: quero comprar 2 brigadeiros e 1 beijinho",
                from_="whatsapp:+14155238886",
                to=numero
            )
            return str(MessagingResponse())

        elif numero in contexto_pos_pagamento:
            if contexto_pos_pagamento[numero] == "aguardando_resposta_pos_pagamento":
                if any(p in mensagem for p in ["não", "nao", "só isso", "so isso", "mais nada"]):
                    resposta = "😊 Obrigado pela preferência! Qualquer coisa, é só chamar. Tenha um ótimo dia! 🍬"
                    contexto_pos_pagamento[numero] = "aguardando_endereco"
                    twilio_client.messages.create(
                        body="📍 Por favor, informe o endereço para entrega do pedido.",
                        from_="whatsapp:+14155238886",
                        to=numero
                    )
                else:
                    resposta = "Certo! Pode me dizer o que mais gostaria de pedir. 🍭"

            elif contexto_pos_pagamento[numero] == "aguardando_endereco":
                enderecos_clientes[numero] = mensagem
                resposta = "📦 Endereço recebido! Seu pedido será enviado em breve. Obrigado novamente! 🍬"
                twilio_client.messages.create(
                    body=f"📢 Novo pedido confirmado!\nCliente: {numero}\nEndereço: {mensagem}",
                    from_="whatsapp:+14155238886",
                    to=NUMERO_DONO
                )
                contexto_pos_pagamento.pop(numero)

        else:
            prompt = (
                f"Você é o AtendeBot, um atendente simpático de uma loja de doces."
                f" Ajude o cliente de forma natural com base na mensagem a seguir:\n{mensagem}"
                f" Pergunte se o cliente deseja ver o catálogo na primeira mensagem que você mandar."
            )
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
                mensagem_confirmacao = (
                    "🎉 Pagamento confirmado! Seu pedido está sendo preparado com carinho. Obrigado! 🍬\n"
                    "Deseja mais alguma coisa? Se não, digite 'não'."
                )
                contexto_pos_pagamento[numero] = "aguardando_resposta_pos_pagamento"

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
                    except Exception as sms_e:
                        print(f"Erro ao enviar SMS: {sms_e}")

    return {"status": "ok"}
