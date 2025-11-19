import streamlit as st
import pandas as pd
import io
import re # Importação da biblioteca de expressões regulares (Regex)

# --- Configuração da Página ---
st.set_page_config(
    page_title="Calculadora de Produção e Buffer", # Título atualizado
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Estilo Tailwind-like (usando CSS inline do Streamlit) ---
st.markdown("""
<style>
.stApp {
    background-color: #f7f9fc;
}
.main-header {
    font-size: 2.5em;
    font-weight: 700;
    color: #1e40af; /* Blue-900 */
    text-align: center;
    margin-bottom: 0.5em;
}
.metric-box {
    background-color: #dbeafe; /* Blue-100 */
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    margin-top: 20px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
    min-height: 120px; /* Garante altura uniforme */
}
.metric-value {
    font-size: 2em;
    font-weight: 800;
    color: #1e40af;
}
.metric-label {
    font-size: 0.9em;
    color: #374151;
}
.analysis-title {
    font-size: 1.5em;
    font-weight: 600;
    color: #0b509f;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}
/* Estilo melhorado para a exibição de lotes agrupados */
.lote-breakdown-box {
    background-color: #ffffff; /* Fundo branco para destaque */
    padding: 15px;
    border: 1px solid #bfdbfe; /* Borda levemente azul */
    border-radius: 6px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06);
}
.lote-prefix-result {
    /* Removido white-space: pre-wrap; e line-height para usar tags <p> aninhadas */
    font-size: 1.2em;
    font-weight: 700;
    color: #1e40af;
}
</style>
""", unsafe_allow_html=True)

# Função para realizar o cálculo principal (diferença de contagens)
def calculate_and_display_counts(df, filter_col, term1, term2):
    """
    Calcula a contagem de duas ocorrências (term1 - term2) em uma coluna e exibe o resultado.
    Utiliza limites de palavra (\b) para garantir a correspondência exata do termo.
    """
    
    # Rótulos para exibição 
    label1 = term1.replace('_', ' ') 
    label2 = term2.replace('_', ' ')
    
    # Adiciona word boundaries (\b) e escapa o termo para uso seguro em regex
    regex1 = r'\b' + re.escape(term1) + r'\b'
    regex2 = r'\b' + re.escape(term2) + r'\b'
    
    # Contagem do Termo 1 (case-insensitive, usando Regex)
    count1 = df[
        df[filter_col].str.contains(regex1, case=False, na=False, regex=True)
    ].shape[0] 
    
    # Contagem do Termo 2 (case-insensitive, usando Regex)
    count2 = df[
        df[filter_col].str.contains(regex2, case=False, na=False, regex=True)
    ].shape[0] 
    
    result = count1 - count2
    
    st.markdown(f'<p class="analysis-title">{label1} vs {label2}</p>', unsafe_allow_html=True)
    
    col_in, col_off, col_total = st.columns(3)

    with col_in:
        st.markdown(f"""
        <div class="metric-box">
            <p class="metric-label">Contagem Total {label1}</p>
            <p class="metric-value">{count1:,}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_off:
         st.markdown(f"""
        <div class="metric-box">
            <p class="metric-label">Contagem Total {label2}</p>
            <p class="metric-value">{count2:,}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_total:
        # Define cores dinâmicas para o resultado final
        bg_color = '#e5e7eb' if result == 0 else ('#d1fae5' if result > 0 else '#fee2e2')
        text_color = '#10b981' if result > 0 else ('#ef4444' if result < 0 else '#6b7280')
        st.markdown(f"""
        <div class="metric-box" style="background-color: {bg_color};">
            <p class="metric-label">Resultado Final ({label1} - {label2})</p>
            <p class="metric-value" style="color: {text_color};">
                {result:,}
            </p>
        </div>
        """, unsafe_allow_html=True)

# Função para realizar a análise diária detalhada por lote (agrupado por prefixo)
def calculate_daily_production_breakdown(df, filter_col, data_col, lote_col, target_terms, selected_date):
    
    # 1. Converter a coluna de Data e Filtrar
    try:
        # Tenta converter a coluna de data para datetime e normaliza para a data (sem hora)
        # Usamos .copy() para evitar SettingWithCopyWarning
        df_copy = df.copy() 
        df_copy['Day_Normalized'] = pd.to_datetime(df_copy[data_col], errors='coerce').dt.normalize()
        
        # Filtra pelo dia selecionado
        df_daily = df_copy[df_copy['Day_Normalized'] == selected_date]
        
        if df_daily.empty:
            st.warning(f"Não foram encontradas linhas na coluna de Termos para a data selecionada: {selected_date.strftime('%Y-%m-%d')}")
            return
            
    except Exception as e:
        st.error(f"Erro ao processar a coluna de Data '{data_col}'. Verifique se a coluna está no formato correto (data/timestamp).")
        st.exception(e)
        return

    # 2. Iterar sobre os termos
    for term in target_terms:
        
        st.markdown(f"### {term.replace('_', ' ')}:")
        
        # 2a. Define o regex exato para o termo
        regex_term = r'\b' + re.escape(term) + r'\b'
        
        # 2b. Filtra o DataFrame diário pelo termo (case-insensitive)
        df_filtered = df_daily[
            df_daily[filter_col].str.contains(regex_term, case=False, na=False, regex=True)
        ]
        
        # 2c. Realiza a agregação: Contagem por Prefixo de Lote (3 primeiras letras)
        if not df_filtered.empty:
            # Garante que a coluna Lote também não tenha valores NaN antes de agrupar
            df_lotes = df_filtered.dropna(subset=[lote_col]).copy()
            
            # CRUCIAL: Cria a coluna de prefixo de lote (3 primeiras letras, maiúsculas)
            df_lotes['Lote_Prefix'] = df_lotes[lote_col].astype(str).str[:3].str.upper()
            
            # Conta o número de ocorrências (linhas) por Prefixo de Lote
            prefix_counts = df_lotes.groupby('Lote_Prefix').size().reset_index(name='Contagem')
            
            # 2d. Formata a saída
            total_count = prefix_counts['Contagem'].sum()
            
            # CORREÇÃO DE ALINHAMENTO APLICADA AQUI: Usando tags <p> para alinhar verticalmente
            output_parts_html = []
            for index, row in prefix_counts.iterrows():
                # Cada item é um <p> sem margens/padding extra, garantindo o alinhamento
                output_parts_html.append(f"<p style='margin: 0; padding: 0;'>{row['Contagem']:,} {row['Lote_Prefix']}</p>")

            # Junta todos os parágrafos em uma única string HTML
            output_string_html = '\n'.join(output_parts_html)
            
            # Novo layout para melhor exibição
            col_total, col_breakdown = st.columns([1, 2])

            with col_total:
                 st.metric(label=f"Total {term.replace('_', ' ')}", value=f"{total_count:,}")
            
            with col_breakdown:
                st.markdown(f"""
                    <div class="lote-breakdown-box">
                        <p class="metric-label" style="text-align: left; color: #1e40af; font-size: 1.0em; margin-bottom: 5px;">Contagem por Prefixo de Lote:</p>
                        <div class="lote-prefix-result">
                            {output_string_html if output_string_html else "<p style='margin: 0; padding: 0;'>Nenhum lote encontrado.</p>"}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"Nenhuma ocorrência de '{term.replace('_', ' ')}' encontrada para o dia selecionado. Total: 0")
        
        st.markdown("---")


# --- Título Principal ---
st.markdown('<p class="main-header">Análise Múltipla de Contagens & Buffer</p>', unsafe_allow_html=True)
st.markdown("---")

# --- Criação das Abas de Alto Nível ---
tab_config, tab_resultados = st.tabs(["Configuração (1 e 2)", "Resultados (3, 4 e 5)"])

# Inicializa variáveis no session state para persistência
if 'df' not in st.session_state:
    st.session_state.df = None
if 'column_names' not in st.session_state:
    st.session_state.column_names = []

# --- TAB 1: Configuração ---
with tab_config:
    st.subheader("1. Carregar Planilha (.csv, .xlsx)")

    uploaded_file = st.file_uploader(
        "Arraste e solte ou clique para carregar sua planilha",
        type=['csv', 'xlsx'],
        accept_multiple_files=False,
        help="O arquivo deve ter colunas para Termos, Dia (Data/Timestamp) e Lote.",
        key="uploader"
    )

    if uploaded_file is not None:
        try:
            # Tenta ler como Excel ou CSV
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                # Tenta ler CSV com detecção automática de delimitador (mais robusto)
                df = pd.read_csv(uploaded_file)
            
            st.session_state.df = df
            st.session_state.column_names = df.columns.tolist()

            st.success(f"Arquivo '{uploaded_file.name}' carregado com sucesso! (Linhas: {len(df)})")

            st.subheader("2. Mapeamento de Colunas")
            st.dataframe(df.head()) # Mostra as primeiras linhas

            column_names = st.session_state.column_names
            default_index = 0

            # Mapeamento de colunas usando session_state para persistência
            filter_col = st.selectbox(
                "Selecione a Coluna de Categorização (Termos - Ex: W_Off):",
                column_names,
                index=default_index,
                key="filter_col_select",
                help="A coluna que possui os identificadores para contagem."
            )
            
            data_col = st.selectbox(
                "Selecione a Coluna do Dia (Data/Timestamp):",
                column_names,
                index=default_index,
                key="data_col_select",
                help="Coluna que contém a data/timestamp para filtragem diária (Ex: Coluna J)."
            )

            lote_col = st.selectbox(
                "Selecione a Coluna do Lote:",
                column_names,
                index=default_index,
                key="lote_col_select",
                help="Coluna que contém o número de lote para detalhamento da contagem (Ex: Coluna L)."
            )
            
            st.markdown("---")
            st.info("Configuração completa! Navegue para a aba 'Resultados' para ver as análises.")

        except Exception as e:
            st.error("Erro ao ler o arquivo. Certifique-se de que o formato do arquivo é .csv ou .xlsx e que ele não está corrompido.")
            st.exception(e)

    else:
        st.info("Aguardando o upload de um arquivo para iniciar a análise...")


# --- TAB 2: Resultados ---
with tab_resultados:
    # Verifica se o DataFrame e as colunas foram configuradas
    if st.session_state.df is None or not st.session_state.column_names:
        st.warning("Por favor, carregue a planilha e configure as colunas na aba 'Configuração (1 e 2)' primeiro.")
    else:
        # Recupera as colunas selecionadas da Configuração
        filter_col = st.session_state["filter_col_select"]
        data_col = st.session_state["data_col_select"]
        lote_col = st.session_state["lote_col_select"]

        df = st.session_state.df
        
        # --- Limpeza e Processamento de Dados ---
        try:
            # Garantir que a coluna de filtro seja tratada como string para a contagem
            df[filter_col] = df[filter_col].astype(str).fillna('')
            df_processed = df
            
            # --- Definição dos Pares de Cálculo ---
            
            # 3. Cálculos Principais (Processo In - Processo Out)
            main_calculations = [
                ('W_In', 'W_Off'),
                ('Painting_In', 'Painting_Out'),
                ('PBS_Off', 'AOFF')
            ]
            
            # 4. Cálculos de Buffer (Etapa Anterior Off - Etapa Seguinte In)
            buffer_calculations = [
                ('W_Off', 'Painting_In'),
                ('Painting_Out', 'PBS_Off'),
                ('AOFF', 'Inspection_off')
            ]

            # --- Criação das Sub-Abas para os Resultados ---
            tab_calculos, tab_diario = st.tabs(["Cálculos de Contagem e Buffer", "Análise de Produção Diária"])

            # --- SUB-ABA 1: Cálculos de Contagem e Buffer ---
            with tab_calculos:
                # --- Execução e Exibição dos Cálculos Principais ---
                st.subheader("3. Resultados de Contagem (In - Out)")
                for term1, term2 in main_calculations:
                    calculate_and_display_counts(df_processed, filter_col, term1, term2)
                    
                st.markdown("---")
                
                # --- Execução e Exibição dos Cálculos de Buffer ---
                st.subheader("4. Resultados do Buffer (Off - In)")
                for term1, term2 in buffer_calculations:
                    calculate_and_display_counts(df_processed, filter_col, term1, term2)
                
            # --- SUB-ABA 2: Análise de Produção Diária ---
            with tab_diario:
                st.subheader("5. Configuração da Análise de Produção Diária (Detalhada por Lote)")

                # Lógica para predefinir o date_input com a data mais recente
                latest_date = pd.to_datetime('today').date()
                if data_col in df_processed.columns and not df_processed[data_col].empty:
                    try:
                        # Converte a coluna de data para obter a data máxima
                        df_processed['Temp_Date'] = pd.to_datetime(df_processed[data_col], errors='coerce').dt.normalize()
                        max_date = df_processed['Temp_Date'].max()
                        if pd.notna(max_date):
                            latest_date = max_date.date()
                    except:
                        pass # Mantém o valor padrão em caso de erro na conversão de data


                selected_date = st.date_input(
                    "Selecione o Dia para Análise Detalhada (Data de Referência):",
                    value=latest_date,
                    key="daily_analysis_date_results"
                )
                
                # Termos de buffer a serem analisados detalhadamente
                daily_buffer_terms = ['W_Off', 'Painting_Out', 'AOFF', 'Inspection_off']
                
                # Botão para executar o cálculo diário detalhado
                if st.button("Executar Análise de Produção Diária", key="run_daily_analysis_btn"):
                    if selected_date:
                        calculate_daily_production_breakdown(
                            df_processed, 
                            filter_col, 
                            data_col, 
                            lote_col, 
                            daily_buffer_terms, 
                            pd.to_datetime(selected_date)
                        )
                    else:
                        st.warning("Por favor, selecione uma data para a análise.")
            
            st.markdown("---")
            
            # --- Exibição Detalhada (para conferência) ---
            
            # Combina todos os termos para o filtro de exibição
            all_terms = main_calculations + buffer_calculations
            all_terms_list = [term for pair in all_terms for term in pair]
            all_terms_regex_list = [r'\b' + re.escape(term) + r'\b' for term in set(all_terms_list)] # Garante termos únicos
            all_terms_regex = '|'.join(all_terms_regex_list)
            
            with st.expander("Ver Detalhes de Todas as Linhas Contadas (Filtro por Termos)"):
                 st.dataframe(
                    df_processed[
                        df_processed[filter_col].str.contains(all_terms_regex, case=False, na=False, regex=True)
                    ]
                )

        except Exception as e:
            st.error(f"Erro ao processar os dados. Verifique se as colunas de filtro selecionadas estão corretas.")
            st.exception(e)