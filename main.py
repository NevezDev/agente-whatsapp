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

    # Resposta automática
    try:
        # Enviando resposta para o número de quem enviou a mensagem
        client.messages.create(
            body="Olá! Recebemos sua mensagem. Em breve responderemos.",
            from_=twilio_number,  # Número do Twilio, passado pela variável de ambiente
            to=From  # Número do remetente
        )
    except Exception as e:
        print("Erro ao enviar resposta:", str(e))
        return JSONResponse(content={"status": f"Erro ao enviar resposta: {str(e)}"}, status_code=400)

    return JSONResponse(content={"status": "Mensagem recebida e resposta enviada."})
