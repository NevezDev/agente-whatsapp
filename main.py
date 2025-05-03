import os
from fastapi import FastAPI, Request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import httpx

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do Twilio
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')

# Configuração do Hugging Face (ou outra IA que você esteja usando)
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/gpt2"  # Usando o GPT-2

app = FastAPI()

@app.post("/whatsapp")
async def whatsapp(request: Request):
    # Recebendo dados do WhatsApp via Twilio
    form_data = await request.form()
    message_body = form_data.get("Body")  # Texto enviado pelo usuário
    from_number = form_data.get("From")  # Número do remetente (para log ou envio de mensagens específicas)

    # Fazendo requisição para a IA para gerar resposta
    async with httpx.AsyncClient() as client:
        # Body para a requisição
        data = {
            "inputs": message_body,
        }

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        }

        try:
            response = await client.post(HUGGINGFACE_API_URL, json=data, headers=headers)
            response.raise_for_status()  # Lança exceção se o código de status HTTP não for 2xx

            # Verificando a estrutura da resposta e acessando corretamente
            if isinstance(response.json(), list) and response.json():
                resposta_chatbot = response.json()[0].get('generated_text', "Desculpe, ocorreu um erro.")
            elif isinstance(response.json(), dict):
                resposta_chatbot = response.json().get('generated_text', "Desculpe, ocorreu um erro.")
            else:
                resposta_chatbot = "Desculpe, ocorreu um erro."

        except httpx.HTTPStatusError as e:
            resposta_chatbot = "Erro ao se comunicar com a API."
            print(f"Erro HTTP: {e}")
        except Exception as e:
            resposta_chatbot = "Erro desconhecido."
            print(f"Erro desconhecido: {e}")

    # Enviar a resposta de volta via Twilio
    resp = MessagingResponse()
    resp.message(resposta_chatbot)  # Mensagem para o WhatsApp
    return str(resp)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
