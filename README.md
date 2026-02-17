# Painel MPEA — OKRs • KRs • Ações • KPIs

## Como rodar
1) Coloque os arquivos na mesma pasta:
- app_streamlit_mpea_okrs_monitor.py
- column_layout.json
- (opcional) MPEA_KRs_KPIs_StreamlitBase.xlsx

2) Instale dependências:
    pip install streamlit pandas openpyxl altair

3) Execute:
    streamlit run app_streamlit_mpea_okrs_monitor.py

## Layout de colunas (column_layout.json)
- order: lista de colunas (aplicada primeiro; as demais vêm ao final)
- width: aceita "small"|"medium"|"large" ou inteiro (pixels), ou string "350"/"350px".

Dica:
- Para perceber a mudança de largura, defina width para TODAS as colunas (ou use pixels).
