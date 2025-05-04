from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import openai
import os
from data import products
from twilio.rest import Client

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

class WhatsAppMessage(BaseModel):
    From: str
    Body: str

def format_products():
    return "\n".join([f"{p['nome']} - R${{p['preco']:.2f}}\n{{p['descricao']}}" for p in products])

def build_prompt(user_message):
    catalog = format_products()
    return (
        f"Você é o AtendeBot, um atendente simpático de uma loja de doces. "
        f"Seu objetivo é ajudar os clientes a escolherem produtos e responder dúvidas com simpatia.\n"
        f"Catálogo:\n{{catalog}}\n\n"
        f"Mensagem do cliente: {{user_message}}\n"
        f"Responda de forma natural e útil."
    )

@app.post("/webhook")
async def webhook(msg: Request):
    form = await msg.form()
    body = form.get("Body")
    sender = form.get("From")

    prompt = build_prompt(body)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um atendente de uma loja de doces, chamado AtendeBot."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = response["choices"][0]["message"]["content"]

        twilio_client.messages.create(
            body=reply,
            from_=f"whatsapp:{{twilio_number}}",
            to=sender
        )

        return JSONResponse(content={"status": "mensagem enviada"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)
