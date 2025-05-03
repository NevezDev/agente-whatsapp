import os
import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Base de dados de produtos
produtos = [
    {"nome": "Bolo de Chocolate", "categoria": "Bolos", "descricao": "Delicioso bolo de chocolate com cobertura cremosa.", "preco": 25.00},
    {"nome": "Brigadeiro Gourmet", "categoria": "Doces", "descricao": "Brigadeiros gourmet feitos com chocolate belga.", "preco": 2.50},
    {"nome": "Cupcake de Morango", "categoria": "Bolos", "descricao": "Cupcakes fofinhos com cobertura de morango natural.", "preco": 5.00},
    {"nome": "Beijinho", "categoria": "Doces", "descricao": "Tradicional beijinho de coco.", "preco": 2.00},
    {"nome": "Torta de Limão", "categoria": "Tortas", "descricao": "Torta de limão com base crocante e recheio cremoso.", "preco": 30.00},
    {"nome": "Bolo de Cenoura", "categoria": "Bolos", "descricao": "Bolo de cenoura com cobertura de chocolate.", "preco": 20.00},
    {"nome": "Cajuzinho", "categoria": "Doces", "descricao": "Doce tradicional de amendoim em formato de caju.", "preco": 2.00},
]

# Função para montar o prompt com o banco de dados embutido
def montar_prompt(mensagem_usuario: str) -> str:
    prompt = (
        "Você é um atendente virtual de uma loja de doces. "
        "Aja com simpatia e naturalidade, como um vendedor experiente. "
        "Com base na seguinte lista de produtos, ajude o cliente a encontrar o que ele deseja:\n\n"
    )
    categorias = {}
    for produto in produtos:
        cat = produto["categoria"]
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(f"- {produto['nome']}: {produto['descricao']} (R${produto['preco']:.2f})")

    for categoria, itens in categorias.items():
        prompt += f"\nCategoria: {categoria}\n" + "\n".join(itens) + "\n"

    prompt += f"\nMensagem do cliente: \"{mensagem_usuario}\"\n"
    prompt += "Responda como se fosse um atendente real, sugerindo os doces adequados, tirando dúvidas e sendo gentil."

    return prompt

# Rota principal para mensagens do WhatsApp (Twilio)
@app.post("/whatsapp")
async def whatsapp(request: Request):
    form = await request.form()
    mensagem = form.get("Body")
    numero = form.get("From")

    if not mensagem:
        return PlainTextResponse("Não recebi nenhuma mensagem.")

    prompt = montar_prompt(mensagem)

    # Chamada para a API da OpenRouter
    try:
        response = await httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("REFERER_URL", "https://seusite.com"),  # opcional
                "X-Title": os.getenv("PROJECT_TITLE", "AtendeBot")
            },
            json={
                "model": "openrouter/claude-3-haiku",  # ou outro modelo suportado
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=20
        )
        response.raise_for_status()
        resposta_bot = response.json()["choices"][0]["message"]["content"]
        return PlainTextResponse(resposta_bot)

    except Exception as e:
        return PlainTextResponse("Desculpe, ocorreu um erro ao tentar responder. Tente novamente em instantes.")
