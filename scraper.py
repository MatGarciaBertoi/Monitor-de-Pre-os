import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime
import os
import time

# --- CONFIGURAÇÕES ---
URL_PRODUTO = 'https://www.mercadolivre.com.br/teclado-gamer-mecnico-blue-switch-led-rgb-usb-computador-notebook-pc-ps4-xbox-cor-preto-digital-informatica/p/MLB51144275'
PRECO_DESEJADO = 180.00 # Defina aqui o preço que você quer pagar

# --- FUNÇÃO DE SCRAPING (CUSTOMIZADA) ---
def extrair_dados(url):
    """
    Extrai o título e o preço de uma página de produto do Mercado Livre.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Verifica se a requisição foi bem-sucedida

        soup = BeautifulSoup(response.content, 'html.parser')

        # --- PARTE CUSTOMIZADA PARA O MERCADO LIVRE ---

        # 1. Extrair o Título
        elemento_titulo = soup.find('h1', class_='ui-pdp-title')
        titulo = elemento_titulo.get_text().strip() if elemento_titulo else "Título não encontrado"

        # 2. Extrair o Preço
        # A classe 'ui-pdp-price__second-line' contém o texto completo, ex: "R$ 209,90"
        elemento_preco = soup.find('div', class_='ui-pdp-price__second-line')
        
        if not elemento_preco:
            print("Elemento do preço não encontrado. O layout do site pode ter mudado.")
            return None, None

        # Limpeza do preço (Ex: "R$ 209,90" -> 209.90)
        # Usamos .find() de novo para pegar o primeiro span com a fração do preço
        preco_texto = elemento_preco.find('span', class_='andes-money-amount__fraction').get_text()
        preco_limpo = re.sub(r'[^\d,]', '', preco_texto).replace(',', '.')

        return titulo, float(preco_limpo)

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return None, None

# --- FUNÇÃO PARA SALVAR OS DADOS (Já tínhamos feito) ---
def salvar_dados(titulo, preco):
    arquivo_csv = 'historico_precos.csv'
    data_hora_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    novo_dado = pd.DataFrame([{
        'data_hora': data_hora_atual,
        'produto': titulo,
        'preco': preco
    }])

    if not os.path.exists(arquivo_csv):
        novo_dado.to_csv(arquivo_csv, index=False)
    else:
        novo_dado.to_csv(arquivo_csv, mode='a', header=False, index=False)
    
    print(f"[{data_hora_atual}] Preço registrado: R$ {preco:.2f}")

# --- FUNÇÃO DE ALERTA (Simples) ---
def verificar_alerta(preco_atual, preco_alvo):
    if preco_atual <= preco_alvo:
        print("\n" + "="*40)
        print(f"!!! ALERTA DE PREÇO ATINGIDO !!!")
        print(f"O produto está custando R$ {preco_atual:.2f}, abaixo da sua meta de R$ {preco_alvo:.2f}")
        print(f"Link: {URL_PRODUTO}")
        print("="*40 + "\n")
        # Aqui é onde você colocaria a lógica para enviar um e-mail.

# --- SCRIPT PRINCIPAL ---
if __name__ == '__main__':
    print("Iniciando monitoramento de preço para o Teclado Mecânico...")
    
    titulo_produto, preco_atual = extrair_dados(URL_PRODUTO)

    if titulo_produto and preco_atual:
        print(f"Produto: {titulo_produto}")
        salvar_dados(titulo_produto, preco_atual)
        verificar_alerta(preco_atual, PRECO_DESEJADO)
    else:
        print("Não foi possível obter os dados do produto.")