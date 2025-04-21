import os
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Inicializando o app FastAPI
app = FastAPI()

# Variáveis de ambiente
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(account_sid, auth_token)

# Dicionário de produtos (simulação)
produtos = {
    "camisa": {"preço": "R$ 50,00", "imagem_url": "https://dw0jruhdg6fis.cloudfront.net/producao/24866653/G/camisa_branca.jpg"},
    "celular": {"preço": "R$ 1200,00", "imagem_url": "https://samsungbrshop.vtexassets.com/arquivos/ids/228494/1000x1000_0000s_0047_SM-A155_Galaxy-A15-LTE_Blue-Black_Front2.jpg?v=638412055449170000"},
}

@app.post("/whatsapp/")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    print(f"Mensagem recebida de {From}: {Body}")

    # Menu inicial com opções
    if Body.lower() == "menu":
        menu_message = (
            "Olá! Bem-vindo ao nosso serviço. Aqui estão as opções disponíveis:\n"
            "1. Consulta de produtos\n"
            "2. Detalhes do produto\n"
            "3. Suporte\n"
            "4. Falar com um atendente\n"
            "Digite o número da opção desejada."
        )
        try:
            # Enviar o menu
            client.messages.create(
                body=menu_message,
                from_=twilio_number,
                to=From
            )
        except Exception as e:
            print("Erro ao enviar resposta:", str(e))
        return JSONResponse(content={"status": "Menu enviado."})

    # Opção para consulta de produtos
    if Body.lower() == "1":
        produtos_lista = "Aqui estão os produtos disponíveis:\n"
        for produto in produtos:
            produtos_lista += f"- {produto.capitalize()}\n"
        produtos_lista += "Escolha um produto para saber mais (ex: Camisa, Celular)."

        try:
            # Enviar lista de produtos
            client.messages.create(
                body=produtos_lista,
                from_=f"whatsapp:{twilio_number}",
                to=From
            )
        except Exception as e:
            print("Erro ao enviar resposta:", str(e))
        return JSONResponse(content={"status": "Lista de produtos enviada."})

    # Opção para detalhes do produto
    if Body.lower() in produtos:
        produto = produtos[Body.lower()]
        imagem_url = produto["imagem_url"]
        preço = produto["preço"]
        
        detalhes_produto = (
            f"Produto: {Body.capitalize()}\n"
            f"Preço: {preço}\n"
            f"Veja o produto na imagem abaixo."
        )

        try:
            # Enviar detalhes do produto
            client.messages.create(
                body=detalhes_produto,
                from_=f"whatsapp:{twilio_number}",
                to=From,
                media_url=[imagem_url],
            )
        except Exception as e:
            print("Erro ao enviar resposta:", str(e))
        return JSONResponse(content={"status": "Detalhes do produto enviados."})

    # Opção para suporte
    if Body.lower() == "3":
        suporte
