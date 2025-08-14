import sqlite3
import urllib.parse
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime
import os
import time
import json
import logging
from dotenv import load_dotenv

# --- Função de Inicializar o banco de dados ---
def inicializar_db():
    conexao = sqlite3.connect('precos.db') # Cria o arquivo do banco de dados
    cursor = conexao.cursor()
    # Cria a tabela 'historico' se ela não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TIMESTAMP NOT NULL,
            produto TEXT NOT NULL,
            preco REAL NOT NULL
        )
    ''')
    conexao.commit()
    conexao.close()

# --- CONFIGURAÇÕES E INICIALIZAÇÃO ---
load_dotenv() # Carrega as variáveis do arquivo .env

# Configura o logging
logging.basicConfig(
    filename='monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Pega as credenciais do Telegram do ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- FUNÇÕES ---
def extrair_dados(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        elemento_titulo = soup.find('h1', class_='ui-pdp-title')
        titulo = elemento_titulo.get_text().strip() if elemento_titulo else "Título não encontrado"

        elemento_preco = soup.find('div', class_='ui-pdp-price__second-line')
        if not elemento_preco:
            return None, None
        
        preco_texto = elemento_preco.find('span', class_='andes-money-amount__fraction').get_text()
        preco_limpo = re.sub(r'[^\d,]', '', preco_texto).replace(',', '.')
        return titulo, float(preco_limpo)
    except Exception as e:
        logging.error(f"Erro ao extrair dados da URL {url}: {e}")
        return None, None

def salvar_dados_db(titulo, preco):
    conexao = sqlite3.connect('precos.db')
    cursor = conexao.cursor()
    data_hora_atual = datetime.now()
    cursor.execute("INSERT INTO historico (data_hora, produto, preco) VALUES (?, ?, ?)",
                   (data_hora_atual, titulo, preco))
    conexao.commit()
    conexao.close()
    logging.info(f"Preço registrado no DB para '{titulo}': R$ {preco:.2f}")

def enviar_alerta_telegram(mensagem):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Credenciais do Telegram não configuradas. Pulando alerta.")
        return
    
    # Codifica a mensagem para ser segura para uma URL
    mensagem_encodada = urllib.parse.quote_plus(mensagem)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={mensagem_encodada}"
    
    try:
        response = requests.get(url)
        
        # Vamos registrar a resposta completa da API para depuração
        resposta_api = response.json()
        logging.info(f"Resposta da API do Telegram: {resposta_api}")

        # Verifica se a resposta da API indica sucesso real
        if resposta_api.get("ok"):
            logging.info("Alerta processado pelo Telegram com sucesso.")
        else:
            logging.error(f"A API do Telegram retornou um erro: {resposta_api.get('description')}")
            
    except Exception as e:
        logging.error(f"Falha CRÍTICA ao enviar alerta via Telegram: {e}")

# --- BLOCO PRINCIPAL (Versão para rodar uma única vez) ---
if __name__ == '__main__':
    # 1. Garante que o banco de dados e a tabela existam
    inicializar_db()
    
    logging.info("================ INICIANDO SCRIPT DE POPULAÇÃO DO DB ===============")
    
    try:
        with open('produtos.json', 'r', encoding='utf-8') as f:
            lista_produtos = json.load(f)
    except FileNotFoundError:
        logging.error("Arquivo 'produtos.json' não encontrado. Encerrando.")
        exit()

    # 2. Roda a verificação uma única vez para todos os produtos
    logging.info("Iniciando rodada ÚNICA de verificação para popular o banco de dados...")
    for produto in lista_produtos:
        logging.info(f"Verificando: {produto['nome']}")
        titulo, preco = extrair_dados(produto['url'])
        
        if titulo and preco:
            salvar_dados_db(titulo, preco) 
            
            if preco <= produto['preco_desejado']:
                mensagem = f"🚨 ALERTA DE PREÇO! 🚨\nProduto: {titulo}\nPreço Atual: R$ {preco:.2f}\nMeta: R$ {produto['preco_desejado']:.2f}\nLink: {produto['url']}"
                enviar_alerta_telegram(mensagem)
        time.sleep(5) # Pausa de 5s entre as requisições para não sobrecarregar
    
    logging.info("Verificação única concluída! O banco de dados foi populado.")
    print("Verificação concluída! O banco de dados 'precos.db' foi criado e/ou populado com os dados atuais.")