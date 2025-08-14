# Arquivo: app.py
import streamlit as st
import pandas as pd
import os

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Preços")
st.title("📊 Dashboard do Monitor de Preços")
st.write("Esta aplicação exibe o histórico de preços coletado pelo seu monitor.")

# --- Carregamento dos Dados ---
ARQUIVO_DADOS = "historico_precos.csv"

@st.cache_data(ttl=600) # Recarrega os dados a cada 10 minutos
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        df = pd.read_csv(ARQUIVO_DADOS)
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        return df
    return pd.DataFrame() # Retorna um DataFrame vazio se o arquivo não existir

df = carregar_dados()

if df.empty:
    st.warning("Ainda não há dados para exibir. Rode o `monitor.py` para começar a coletar preços.")
else:
    # --- Interface ---
    st.sidebar.header("Filtros")
    produtos_disponiveis = ["Todos"] + list(df['produto'].unique())
    produto_selecionado = st.sidebar.selectbox("Selecione um Produto:", produtos_disponiveis)

    if produto_selecionado != "Todos":
        df_filtrado = df[df['produto'] == produto_selecionado]
    else:
        df_filtrado = df
    
    # --- Exibição dos Dados ---
    st.header(f"Exibindo dados para: {produto_selecionado}")

    # Gráfico
    st.subheader("Gráfico de Evolução de Preços")
    if not df_filtrado.empty:
        st.line_chart(
            df_filtrado.rename(columns={'data_hora':'index'}).set_index('index')['preco']
        )
    else:
        st.info("Não há dados para o produto selecionado.")

    # Tabela de Dados
    st.subheader("Histórico Detalhado")
    st.dataframe(df_filtrado)

    # Botão para recarregar
    if st.button("Recarregar Dados"):
        st.cache_data.clear()
        st.experimental_rerun()