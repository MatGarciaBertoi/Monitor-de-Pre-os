import sqlite3
import urllib.parse
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import time
import json
import logging
from dotenv import load_dotenv

# --- CLASSE PARA GERENCIAR O BANCO DE DADOS ---
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conexao = sqlite3.connect(self.db_file, check_same_thread=False)
        self._inicializar_tabela()

    def _inicializar_tabela(self):
        cursor = self.conexao.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TIMESTAMP NOT NULL,
                produto TEXT NOT NULL,
                preco REAL NOT NULL
            )
        ''')
        self.conexao.commit()

    def salvar_preco(self, titulo, preco):
        cursor = self.conexao.cursor()
        data_hora_atual = datetime.now()
        cursor.execute("INSERT INTO historico (data_hora, produto, preco) VALUES (?, ?, ?)",
                    (data_hora_atual, titulo, preco))
        self.conexao.commit()
        logging.info(f"Preço registrado no DB para '{titulo}': R$ {preco:.2f}")
    
    def __del__(self):
        """Garante que a conexão seja fechada ao final."""
        if self.conexao:
            self.conexao.close()


# --- CLASSE PARA ENVIAR NOTIFICAÇÕES ---
class Notifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def enviar_alerta(self, mensagem):
        if not self.token or not self.chat_id:
            logging.warning("Credenciais do Telegram não configuradas. Pulando alerta.")
            return
        
        mensagem_encodada = urllib.parse.quote_plus(mensagem)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={mensagem_encodada}"
        
        try:
            response = requests.get(url)
            resposta_api = response.json()
            logging.info(f"Resposta da API do Telegram: {resposta_api}")
            if not resposta_api.get("ok"):
                logging.error(f"A API do Telegram retornou um erro: {resposta_api.get('description')}")
        except Exception as e:
            logging.error(f"Falha CRÍTICA ao enviar alerta via Telegram: {e}")


# --- CLASSE ESPECIALIZADA EM SCRAPING DO MERCADO LIVRE ---
class MercadoLivreScraper:
    def __init__(self, url):
        self.url = url
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    def extrair_dados(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            elemento_titulo = soup.find('h1', class_='ui-pdp-title')
            titulo = elemento_titulo.get_text(strip=True) if elemento_titulo else "Título não encontrado"

            elemento_preco = soup.find('div', class_='ui-pdp-price__second-line')
            if not elemento_preco:
                return None, None
            
            preco_texto = elemento_preco.find('span', class_='andes-money-amount__fraction').get_text(strip=True)
            preco_limpo = re.sub(r'[^\d,]', '', preco_texto).replace(',', '.')
            return titulo, float(preco_limpo)
        except Exception as e:
            logging.error(f"Erro ao extrair dados da URL {self.url}: {e}")
            return None, None


# --- SCRAPING DA AMAZON ---
class AmazonScraper:
    def __init__(self, url):
        self.url = url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/'
        }

    def extrair_dados(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            elemento_titulo = soup.find('span', id='productTitle')
            titulo = elemento_titulo.get_text(strip=True) if elemento_titulo else "Título não encontrado"

            # Na Amazon, o preço é dividido em duas partes
            preco_reais = soup.find('span', class_='a-price-whole')
            preco_centavos = soup.find('span', class_='a-price-fraction')

            if not preco_reais:
                return None, None
            
            preco_texto = preco_reais.get_text(strip=True) + (preco_centavos.get_text(strip=True) if preco_centavos else '00')
            preco_limpo = re.sub(r'[^\d,]', '', preco_texto).replace(',', '.')
            return titulo, float(preco_limpo)
        except Exception as e:
            logging.error(f"Erro ao extrair dados da URL {self.url}: {e}")
            return None, None


# --- CLASSE PRINCIPAL, A ORQUESTRADORA  ---
class PriceMonitor:
    def __init__(self, products_file, db_file):
        load_dotenv()
        logging.basicConfig(filename='monitor.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
        
        self.db_manager = DatabaseManager(db_file)
        self.notifier = Notifier(os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))
        
        try:
            with open(products_file, 'r', encoding='utf-8') as f:
                self.lista_produtos = json.load(f)
        except FileNotFoundError:
            logging.error(f"Arquivo '{products_file}' não encontrado. Encerrando.")
            self.lista_produtos = []

    def rodar_verificacao(self, executar_uma_vez=False):
        if not self.lista_produtos:
            return

        logging.info("================ INICIANDO MONITOR (OOP) ===============")
        
        while True:
            logging.info("Iniciando nova rodada de verificação...")
            for produto in self.lista_produtos:
                logging.info(f"Verificando: {produto['nome']} ({produto.get('loja', 'mercadolivre')})")
                
                # --- LÓGICA PARA ESCOLHER O SCRAPER CORRETO ---
                loja = produto.get('loja', 'mercadolivre') # Padrão é mercadolivre se não especificado
                if loja == 'amazon':
                    scraper = AmazonScraper(produto['url'])
                else:
                    scraper = MercadoLivreScraper(produto['url'])
                
                titulo, preco = scraper.extrair_dados()
                
                if titulo and preco:
                    self.db_manager.salvar_preco(titulo, preco)
                    
                    if preco <= produto['preco_desejado']:
                        mensagem = f"🚨 ALERTA DE PREÇO! 🚨\nProduto: {titulo}\nPreço Atual: R$ {preco:.2f}\nMeta: R$ {produto['preco_desejado']:.2f}\nLink: {produto['url']}"
                        self.notifier.enviar_alerta(mensagem)
                
                time.sleep(5)
            
            if executar_uma_vez:
                logging.info("Verificação única concluída!")
                break

            logging.info(f"Verificação concluída. Próxima em 60 segundos.")
            time.sleep(60)


# --- BLOCO DE EXECUÇÃO ---
if __name__ == '__main__':
    monitor = PriceMonitor(products_file='produtos.json', db_file='precos.db')
    monitor.rodar_verificacao(executar_uma_vez=True)
    
    print("Verificação concluída! O banco de dados foi populado.")