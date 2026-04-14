import os
import re
import requests
import smtplib
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from email.message import EmailMessage
from supabase import create_client, Client

# Carrega as variáveis do .env
load_dotenv()

SEU_EMAIL = os.getenv('SEU_EMAIL')
SENHA_APP_EMAIL = os.getenv('SENHA_APP_EMAIL')
ML_ACCESS_TOKEN = os.getenv('ML_ACCESS_TOKEN')

# Novos parâmetros para a biblioteca oficial
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Inicializa o cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def extrair_info_ml(url):
    """
    Retorna o ID e o Tipo (items ou products) baseado na URL.
    """
    # Identifica se é Produto de Catálogo (/p/MLB...)
    match_product = re.search(r'/p/(MLB\d+)', url)
    if match_product:
        return match_product.group(1), "products"
    
    # Identifica se é Item comum (MLB...)
    match_item = re.search(r'(MLB\d+|MLB-\d+)', url)
    if match_item:
        clean_id = match_item.group(1).replace('-', '')
        return clean_id, "items"
        
    return None, None

def enviar_email(preco, titulo, link):
    msg = EmailMessage()
    msg['Subject'] = f"Alerta Mercado Livre: R$ {preco:.2f}!"
    msg['From'] = SEU_EMAIL
    msg['To'] = SEU_EMAIL
    
    corpo_email = f"O produto baixou!\n\nProduto: {titulo}\nPreço Atual: R$ {preco:.2f}\n\nLink: {link}"
    msg.set_content(corpo_email)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SEU_EMAIL, SENHA_APP_EMAIL)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Erro email: {e}")

# ==========================================
# ROTAS DA API
# ==========================================

@app.route('/adicionar_link', methods=['POST'])
def adicionar_link():
    """Rota para cadastrar um novo produto usando a biblioteca Supabase."""
    dados = request.json
    link = dados.get('link')
    preco_desejado = dados.get('preco')

    if not link or preco_desejado is None:
        return jsonify({"erro": "Parâmetros 'link' e 'preco' são obrigatórios"}), 400

    try:
        # Usando a biblioteca oficial para inserir dados
        response = supabase.table("links").insert({
            "link": link, 
            "preco": float(preco_desejado)
        }).execute()
        
        return jsonify({"mensagem": "Link salvo com sucesso!", "dados": response.data}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/verificar_precos', methods=['GET', 'POST'])
def verificar_precos():
    try:
        response = supabase.table("links").select("*").execute()
        produtos = response.data
    except Exception as e:
        return jsonify({"erro": f"Erro Supabase: {str(e)}"}), 500

    resultados = []
    headers = {
        "Authorization": f"Bearer {ML_ACCESS_TOKEN}"
    }

    for produto in produtos:
        link = produto['link']
        preco_alvo = produto['preco']
        
        id_ml, tipo_api = extrair_info_ml(link)
        
        if not id_ml:
            resultados.append({"link": link, "status": "Erro: ID não identificado"})
            continue

        # Define a URL da API baseada no tipo (items ou products)
        url_api = f"https://api.mercadolibre.com/{tipo_api}/{id_ml}"
        
        try:
            resposta = requests.get(url_api, headers=headers)
            
            if resposta.status_code == 200:
                dados_ml = resposta.json()
                
                # Extração de preço varia conforme o tipo
                if tipo_api == "products":
                    # No catálogo, o preço vem do vencedor da 'Buy Box'
                    winner = dados_ml.get('buy_box_winner')
                    preco_atual = winner.get('price') if winner else None
                    titulo = dados_ml.get('name')
                else:
                    # No item comum, o preço é direto
                    preco_atual = dados_ml.get('price')
                    titulo = dados_ml.get('title')

                if preco_atual is None:
                    resultados.append({"produto": titulo, "status": "Erro: Preço não disponível no momento"})
                    continue

                atingiu_meta = preco_atual <= preco_alvo
                
                if atingiu_meta:
                    enviar_email(preco_atual, titulo, link)
                
                resultados.append({
                    "produto": titulo,
                    "preco_atual": preco_atual,
                    "preco_alvo": preco_alvo,
                    "status": "Alerta enviado" if atingiu_meta else "Preço ainda alto",
                    "tipo": tipo_api
                })
            else:
                resultados.append({"id_ml": id_ml, "status": f"Erro API ML ({resposta.status_code})"})
                
        except Exception as e:
            resultados.append({"id_ml": id_ml, "status": f"Erro de requisição: {e}"})

    return jsonify({"resultados_verificacao": resultados}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)