import os
from fastapi import FastAPI, Request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import httpx

# Carrega variáveis do .env
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

app = FastAPI()

# Banco de dados de doces
doces = [
    {"nome": "Beijinho", "categoria": "doces", "descricao": "Docinho de coco com leite condensado", "preco": 1.50},
    {"nome": "Brigadeiro", "categoria": "doces", "descricao": "Clássico de chocolate com granulado", "preco": 1.50},
    {"nome": "Bolo de chocolate", "categoria": "bolos", "descricao": "Bolo de chocolate com cobertura cremosa", "preco": 20.00},
    {"nome": "Mousse de maracujá", "categoria": "mousses", "descricao": "Sobremesa leve e refrescante", "preco": 5.00}
]

def formatar_cardapio():
    texto = "🍬 *Nosso Cardápio* 🍬\n\n"
    for item in doces:
        texto += f"*{item['nome']}* ({item['categoria']}) - R${item['preco']:.2f}\n  _{item['descricao']}_\n\n"
    return texto.strip()

@app.post("/whatsapp")
async def whatsapp(request: Request):
    form_data = await request.form()
    message_body = form_data.get("Body")
    from_number = form_data.get("From")

    # Verifica se o usuário pediu o cardápio
    if message_body.lower() in ["cardápio", "menu", "lista", "doces", "bolos"]:
        resposta = formatar_cardapio()
    else:
        # Integração com DeepSeek
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"Responda como se fosse um atendente simpático de uma loja de doces. Use o seguinte cardápio: {formatar_cardapio()}"

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": message_body}
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(DEEPSEEK_API_URL, json=data, headers=headers)
                response.raise_for_status()
                resposta = response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("Erro:", e)
            resposta = "Desculpe, não consegui responder agora. Tente novamente em instantes."

    twilio_response = MessagingResponse()
    twilio_response.message(resposta)
    return str(twilio_response)
