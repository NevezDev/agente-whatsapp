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

# Configuração do DeepSeek (substitua com seu endpoint do DeepSeek se necessário)
DEEPSEEK_API_URL = "http://seu-endpoint-deepseek"  # Substitua pelo endpoint real
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Banco de dados de doces integrado no código
produtos = [
    {"nome": "Beijinho", "categoria": "Doces", "descricao": "Doce de coco", "preco": 2.50},
    {"nome": "Bolo de Chocolate", "categoria": "Bolos", "descricao": "Bolo fofinho de chocolate", "preco": 10.00},
    {"nome": "Mousse de Maracujá", "categoria": "Doces", "descricao": "Mousse suave de maracujá", "preco": 7.00},
    # Adicione mais produtos conforme necessário
]

# Inicializa o FastAPI
app = FastAPI()

@app.post("/whatsapp")
async def whatsapp(request: Request):
    # Recebendo dados do WhatsApp via Twilio
    form_data = await request.form()
    message_body = form_data.get("Body")
    from_number = form_data.get("From")

    # Procurar no banco de dados se o usuário pediu algo relacionado a doces
    resposta_chatbot = "Desculpe, não entendi sua mensagem."
    for produto in produtos:
        if produto["nome"].lower() in message_body.lower():
            resposta_chatbot = f"Você escolheu {produto['nome']}. Descrição: {produto['descricao']}. Preço: R${produto['preco']:.2f}"
            break
    else:
        # Caso não encontre nenhum produto, fazer requisição para o DeepSeek para gerar a resposta
        async with httpx.AsyncClient() as client:
            data = {
                "inputs": message_body,
            }
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            }

            try:
                response = await client.post(DEEPSEEK_API_URL, json=data, headers=headers)
                response.raise_for_status()

                # Verificar a resposta do modelo
                if isinstance(response.json(), dict):
                    resposta_chatbot = response.json().get('generated_text', "Desculpe, ocorreu um erro.")
                else:
                    resposta_chatbot = "Desculpe, ocorreu um erro com a IA."
            except httpx.HTTPStatusError as e:
                resposta_chatbot = "Erro ao se comunicar com a API DeepSeek."
                print(f"Erro HTTP: {e}")
            except Exception as e:
                resposta_chatbot = "Erro desconhecido."
                print(f"Erro desconhecido: {e}")

    # Enviar a resposta de volta via Twilio
    resp = MessagingResponse()
    resp.message(resposta_chatbot)
    return str(resp)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
