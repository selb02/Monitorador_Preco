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

# Novos parâmetros para a biblioteca oficial
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Inicializa o cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def extrair_id_ml(url):
    """Usa Regex para extrair o ID do Mercado Livre (ex: MLB123456)."""
    match_wid = re.search(r'wid=(MLB\d+)', url)
    if match_wid:
        return match_wid.group(1)
    
    match_padrao = re.search(r'(MLB\d+)', url)
    if match_padrao:
        return match_padrao.group(1)
        
    return None

def enviar_email(preco, titulo, link):
    """Envia o email de alerta."""
    msg = EmailMessage()
    msg['Subject'] = f"Alerta Mercado Livre: Baixou para R$ {preco:.2f}!"
    msg['From'] = SEU_EMAIL
    msg['To'] = SEU_EMAIL
    
    corpo_email = f"O produto baixou!\n\nProduto: {titulo}\nPreço Atual: R$ {preco:.2f}\n\nCompre aqui: {link}"
    msg.set_content(corpo_email)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(SEU_EMAIL, SENHA_APP_EMAIL)
        server.send_message(msg)
        print(f"ALERTA ENVIADO: {titulo}")
        server.quit()
    except Exception as e:
        print(f"Erro ao enviar email: {e}")

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
    """Rota que varre o banco via cliente Supabase, checa a API do ML e envia os emails."""
    try:
        # Usando a biblioteca oficial para buscar todos os dados
        response = supabase.table("links").select("*").execute()
        produtos = response.data
    except Exception as e:
        return jsonify({"erro": f"Erro no Supabase: {str(e)}"}), 500

    resultados = []

    for produto in produtos:
        db_id = produto['id']
        link = produto['link']
        preco_alvo = produto['preco']
        
        id_ml = extrair_id_ml(link)
        
        if not id_ml:
            resultados.append({"link": link, "status": "Erro: ID do ML não encontrado"})
            continue

        url_api = f"https://api.mercadolibre.com/items/{id_ml}"
        
        try:
            resposta = requests.get(url_api)
            if resposta.status_code == 200:
                dados_ml = resposta.json()
                preco_atual = float(dados_ml.get('price'))
                titulo = dados_ml.get('title')
                
                if preco_atual <= preco_alvo:
                    enviar_email(preco_atual, titulo, link)
                    resultados.append({"produto": titulo, "preco_atual": preco_atual, "status": "Alerta enviado"})
                else:
                    resultados.append({"produto": titulo, "preco_atual": preco_atual, "status": "Preço ainda alto"})
            else:
                resultados.append({"id_ml": id_ml, "status": f"Erro na API ML ({resposta.status_code})"})
                
        except Exception as e:
            resultados.append({"id_ml": id_ml, "status": f"Erro de requisição: {e}"})

    return jsonify({"resultados_verificacao": resultados}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)