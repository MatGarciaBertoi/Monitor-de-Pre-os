# Arquivo: app.py (Versão Melhorada)
import streamlit as st
import pandas as pd
import os
import plotly.express as px # Importamos a nova biblioteca
import sqlite3

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Preços")
st.title("📊 Dashboard do Monitor de Preços")
st.write("Esta aplicação exibe o histórico de preços coletado pelo seu monitor.")

# --- Carregamento dos Dados ---
ARQUIVO_DADOS = "historico_precos.csv"

@st.cache_data(ttl=300)
def carregar_dados_db():
    if os.path.exists('precos.db'):
        conexao = sqlite3.connect('precos.db')
        # O Pandas lê diretamente de uma query SQL!
        df = pd.read_sql_query("SELECT * FROM historico", conexao)
        conexao.close()
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        return df
    return pd.DataFrame()

df = carregar_dados_db()

if df.empty:
    st.warning("Ainda não há dados para exibir. Rode o `monitor.py` para começar a coletar preços.")
else:
    # --- Interface da Barra Lateral ---
    st.sidebar.header("Filtros")
    # Carrega a lista de produtos do arquivo JSON para saber a meta de cada um
    try:
        with open('produtos.json', 'r', encoding='utf-8') as f:
            produtos_config = {item['nome']: item for item in pd.read_json(f).to_dict('records')}
    except FileNotFoundError:
        produtos_config = {}

    produtos_disponiveis = ["Visão Geral"] + list(df['produto'].unique())
    produto_selecionado_nome_longo = st.sidebar.selectbox("Selecione um Produto:", produtos_disponiveis)

    # --- Lógica para filtrar os dados ---
    if produto_selecionado_nome_longo != "Visão Geral":
        df_filtrado = df[df['produto'] == produto_selecionado_nome_longo]
        # Pega o primeiro nome do produto para usar como chave no dicionário de config
        produto_config_key = next((key for key in produtos_config if key in produto_selecionado_nome_longo), None)
    else:
        df_filtrado = df
        produto_config_key = None
        
    st.header(f"Exibindo dados para: {produto_selecionado_nome_longo}")

    # --- NOVO: Métricas (KPIs) ---
    if not df_filtrado.empty:
        col1, col2, col3 = st.columns(3)
        
        # Pega o preço mais recente
        preco_atual = df_filtrado.sort_values(by='data_hora', ascending=False).iloc[0]['preco']
        col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")

        # Pega o menor preço do histórico
        menor_preco = df_filtrado['preco'].min()
        col2.metric("Menor Preço Histórico", f"R$ {menor_preco:.2f}")
        
        # Mostra a meta de preço, se um produto específico for selecionado
        if produto_config_key and produto_config_key in produtos_config:
            meta_preco = produtos_config[produto_config_key]['preco_desejado']
            col3.metric("Meta de Preço", f"R$ {meta_preco:.2f}")
        else:
            col3.metric("Meta de Preço", "-")

    # --- NOVO: Gráfico Interativo com Plotly ---
    st.subheader("Gráfico de Evolução de Preços")
    if not df_filtrado.empty:
        # Se for 'Visão Geral', colore o gráfico por produto
        fig = px.line(df_filtrado, x='data_hora', y='preco', 
                      color='produto' if produto_selecionado_nome_longo == 'Visão Geral' else None,
                      markers=True,
                      labels={"data_hora": "Data", "preco": "Preço (R$)", "produto": "Produto"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados para exibir.")

    # Tabela de Dados
    st.subheader("Histórico Detalhado")
    st.dataframe(df_filtrado)

    # Botão para recarregar
    if st.button("Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()