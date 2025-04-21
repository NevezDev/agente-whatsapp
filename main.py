import os
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Variáveis de ambiente
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(account_sid, auth_token)

@app.post("/whatsapp/")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    print(f"Mensagem recebida de {From}: {Body}")

    # Respostas Condicionais
    response_message = ""
    if "olá" in Body.lower():
        response_message = "Olá! Como posso ajudar você hoje?"
    elif "ajuda" in Body.lower():
        response_message = "Aqui estão algumas coisas que posso fazer por você:\n- Responder dúvidas\n- Informar o status do seu pedido\n- Falar sobre produtos"
    elif "preço" in Body.lower():
        response_message = "O preço do nosso produto X é R$ 199,90."
    elif "obrigado" in Body.lower():
        response_message = "De nada! Fico à disposição!"
    else:
        response_message = "Desculpe, não entendi sua mensagem. Você pode digitar 'ajuda' para ver as opções."

    # Enviar a resposta
    try:
        message = client.messages.create(
            body=response_message,
            from_=twilio_number,
            to=From
        )
    except Exception as e:
        print("Erro ao enviar resposta:", str(e))

    return JSONResponse(content={"status": "Mensagem recebida e resposta enviada."})

