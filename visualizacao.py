# Arquivo: visualizacao.py

import pandas as pd
import matplotlib.pyplot as plt

def gerar_grafico():
    """
    Lê o arquivo CSV com o histórico de preços e gera um gráfico.
    """
    arquivo_csv = 'historico_precos.csv'
    
    try:
        # Tenta ler o arquivo de dados
        df = pd.read_csv(arquivo_csv)
        
        # Garante que o arquivo não está vazio
        if df.empty:
            print("O arquivo de histórico 'historico_precos.csv' está vazio. Execute o monitor primeiro.")
            return

        # Converte a coluna de data/hora para o formato de data do Python
        df['data_hora'] = pd.to_datetime(df['data_hora'])

        # Cria a figura e o gráfico
        plt.figure(figsize=(12, 7))
        plt.plot(df['data_hora'], df['preco'], marker='o', linestyle='-', color='b')

        # Customização do gráfico
        plt.title(f'Histórico de Preços - {df["produto"].iloc[0][:30]}...') # Pega os 30 primeiros caracteres do nome
        plt.xlabel('Data e Hora da Verificação')
        plt.ylabel('Preço (R$)')
        plt.grid(True)
        plt.xticks(rotation=45) # Rotaciona as legendas do eixo X para não sobrepor
        plt.tight_layout() # Ajusta o layout para garantir que tudo caiba na imagem

        # Salva o gráfico como uma imagem PNG
        nome_arquivo_grafico = 'historico_precos.png'
        plt.savefig(nome_arquivo_grafico)
        print(f"Gráfico '{nome_arquivo_grafico}' gerado/atualizado com sucesso.")

    except FileNotFoundError:
        print(f"Arquivo '{arquivo_csv}' não encontrado. Execute o script de monitoramento primeiro para criar o histórico.")
    except Exception as e:
        print(f"Ocorreu um erro ao gerar o gráfico: {e}")

if __name__ == '__main__':
    gerar_grafico()