# Arquivo: monitor.py
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

# AJUSTE DE VELOCIDADE PARA TESTES
# Alterado para 60 segundos (1 minuto) para testes locais.
# O valor original para produção era 3600 (1 hora).
INTERVALO_VERIFICACAO = 60  

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

def salvar_dados(titulo, preco):
    arquivo_csv = 'historico_precos.csv'
    data_hora_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    novo_dado = pd.DataFrame([{'data_hora': data_hora_atual, 'produto': titulo, 'preco': preco}])
    
    if not os.path.exists(arquivo_csv):
        novo_dado.to_csv(arquivo_csv, index=False, encoding='utf-8')
    else:
        novo_dado.to_csv(arquivo_csv, mode='a', header=False, index=False, encoding='utf-8')
    logging.info(f"Preço registrado para '{titulo}': R$ {preco:.2f}")

def enviar_alerta_telegram(mensagem):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Credenciais do Telegram não configuradas. Pulando alerta.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={mensagem}"
    try:
        requests.get(url)
        logging.info("Alerta enviado via Telegram com sucesso.")
    except Exception as e:
        logging.error(f"Falha ao enviar alerta via Telegram: {e}")

# --- LOOP PRINCIPAL ---
if __name__ == '__main__':
    logging.info("================ INICIANDO MONITOR (MODO TESTE) ===============")
    
    try:
        with open('produtos.json', 'r', encoding='utf-8') as f:
            lista_produtos = json.load(f)
    except FileNotFoundError:
        logging.error("Arquivo 'produtos.json' não encontrado. Encerrando.")
        exit()

    while True:
        logging.info("Iniciando nova rodada de verificação...")
        for produto in lista_produtos:
            logging.info(f"Verificando: {produto['nome']}")
            titulo, preco = extrair_dados(produto['url'])
            
            if titulo and preco:
                salvar_dados(titulo, preco)
                if preco <= produto['preco_desejado']:
                    mensagem = f"🚨 ALERTA DE PREÇO! 🚨\nProduto: {titulo}\nPreço Atual: R$ {preco:.2f}\nMeta: R$ {produto['preco_desejado']:.2f}\nLink: {produto['url']}"
                    enviar_alerta_telegram(mensagem)
            time.sleep(10) # Pausa de 10s para não sobrecarregar o site
        
        logging.info(f"Verificação concluída. Próxima em {INTERVALO_VERIFICACAO} segundos.")
        time.sleep(INTERVALO_VERIFICACAO)