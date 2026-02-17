import json
import os
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Painel OKRs/KRs/KPIs — MPEA", layout="wide")

FILE_DEFAULT = "data/MPEA_KRs_KPIs_StreamlitBase.xlsx"
LAYOUT_FILE = "column_layout.json"  # edite este arquivo diretamente
LOGO_FILE = "pea_logo.png"          # PNG com fundo transparente (opcional)

# ────────────────────────────────────────────────
#   Layout helpers (JSON read-only)
# ────────────────────────────────────────────────
def _default_layout():
    return {
        "okrs": {
            "order": ["_selected", "OKR_ID", "Eixo_CAPES", "Objetivo_OKR"],
            "width": {},
            "labels": {"OKR_ID": "OKR", "Eixo_CAPES": "Eixo CAPES", "Objetivo_OKR": "Objetivo"}
        },
        "krs": {
            "order": ["_selected", "KR_ID", "OKR_ID", "Resultado-chave", "Meta_2028", "Frequência"],
            "width": {},
            "labels": {"KR_ID": "KR", "OKR_ID": "OKR", "Resultado-chave": "Resultado-chave", "Meta_2028": "Meta 2028", "Frequência": "Frequência"}
        },
        "acoes": {
            "order": ["_selected", "ID", "EIXO", "O QUÊ?", "STATUS", "OKR_USED", "KR_ID_USADA"],
            "width": {},
            "labels": {"ID": "ID", "EIXO": "Eixo", "O QUÊ?": "O quê?", "STATUS": "Status", "OKR_USED": "OKR", "KR_ID_USADA": "KR"}
        },
        "kpis": {
            "order": ["_selected", "KPI_ID", "KPI", "OKRs_relacionadas", "Unidade", "Frequência", "Fonte"],
            "width": {},
            "labels": {"KPI_ID": "KPI", "KPI": "Indicador", "OKRs_relacionadas": "OKRs", "Unidade": "Unidade", "Frequência": "Frequência", "Fonte": "Fonte"}
        },
        "__global__": {"labels": {"_selected": "Selecionado"}}
    }

def load_layout(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict):
            return obj
    return _default_layout()

def _apply_order_and_hide(df: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    cols = [c for c in order if c in df.columns]
    if not cols:
        return df
    return df[cols]

def _parse_width(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("small", "medium", "large"):
            return s
        if s.endswith("px"):
            s = s[:-2].strip()
        if s.isdigit():
            return int(s)
    return None

def _label_for(col: str, table_labels: dict, global_labels: dict) -> str:
    return str(table_labels.get(col, global_labels.get(col, col)))

def build_column_config(df: pd.DataFrame, width_map: dict, labels_map: dict, global_labels: dict, default_width="medium") -> dict:
    cfg = {}
    for col in df.columns:
        display = _label_for(col, labels_map, global_labels)
        if col == "_selected":
            cfg[col] = st.column_config.CheckboxColumn(display, default=False, width="small")
            continue
        w = _parse_width(width_map.get(col))
        if w is None:
            w = default_width
        cfg[col] = st.column_config.TextColumn(display, width=w)
    return cfg

# ────────────────────────────────────────────────
#   load_data
# ────────────────────────────────────────────────
@st.cache_data
def load_data(file_path):
    xl = pd.ExcelFile(file_path)
    okrs = pd.read_excel(xl, "OKRs")
    krs = pd.read_excel(xl, "KRs")
    kpis = pd.read_excel(xl, "KPIs")
    okr_kpi = pd.read_excel(xl, "OKR_KPI")
    acoes = pd.read_excel(xl, "Ações_KR")

    okrs["OKR_ID"] = okrs["OKR_ID"].astype(str).str.strip()
    krs["KR_ID"] = krs["KR_ID"].astype(str).str.strip()
    krs["OKR_ID"] = krs["OKR_ID"].astype(str).str.strip()
    kpis["KPI_ID"] = kpis["KPI_ID"].astype(str).str.strip()
    okr_kpi["OKR_ID"] = okr_kpi["OKR_ID"].astype(str).str.strip()
    okr_kpi["KR_ID"] = okr_kpi["KR_ID"].astype(str).str.strip()
    okr_kpi["KPI_ID"] = okr_kpi["KPI_ID"].astype(str).str.strip()

    acoes["ID"] = acoes["ID"].astype(str).str.strip()

    if "KR_ID_USADA" not in acoes.columns:
        if "KR_ID_FINAL" in acoes.columns and "KR_ID_SUGERIDA" in acoes.columns:
            final = acoes["KR_ID_FINAL"].astype(str).replace({"nan": "", "None": ""}).str.strip()
            sug = acoes["KR_ID_SUGERIDA"].astype(str).replace({"nan": "", "None": ""}).str.strip()
            acoes["KR_ID_USADA"] = final.where(final != "", sug)
        else:
            acoes["KR_ID_USADA"] = acoes.get("KR_ID_SUGERIDA", "").astype(str)
    acoes["KR_ID_USADA"] = acoes["KR_ID_USADA"].astype(str).replace({"nan": "", "None": ""}).str.strip()

    if "OKR_USED" not in acoes.columns:
        acoes["OKR_USED"] = acoes.get("OKR_ID_SUGERIDA", "")
    acoes["OKR_USED"] = acoes["OKR_USED"].astype(str).replace({"nan": "", "None": ""}).str.strip()

    return okrs, krs, kpis, okr_kpi, acoes

# ────────────────────────────────────────────────
#   filter_views
# ────────────────────────────────────────────────
def filter_views(okrs, krs, kpis, okr_kpi, acoes, sel_okr=None, sel_kr=None, sel_acao=None, sel_kpi=None):
    kr_to_okr = dict(zip(krs["KR_ID"], krs["OKR_ID"]))

    if sel_acao:
        arow = acoes[acoes["ID"] == sel_acao]
        if len(arow):
            kr_id = arow["KR_ID_USADA"].iloc[0]
            okr_id = arow["OKR_USED"].iloc[0] or kr_to_okr.get(kr_id, "")
            okrs_v = okrs[okrs["OKR_ID"] == okr_id] if okr_id else okrs
            krs_v = krs[krs["KR_ID"] == kr_id]
            acoes_v = acoes[acoes["ID"] == sel_acao]
            kpi_ids = okr_kpi[okr_kpi["KR_ID"] == kr_id]["KPI_ID"].unique().tolist()
            kpis_v = kpis[kpis["KPI_ID"].isin(kpi_ids)] if kpi_ids else kpis.iloc[0:0]
            return okrs_v, krs_v, acoes_v, kpis_v

    if sel_kpi:
        kr_ids = okr_kpi[okr_kpi["KPI_ID"] == sel_kpi]["KR_ID"].unique().tolist()
        okr_ids = okr_kpi[okr_kpi["KPI_ID"] == sel_kpi]["OKR_ID"].unique().tolist()
        okrs_v = okrs[okrs["OKR_ID"].isin(okr_ids)] if okr_ids else okrs.iloc[0:0]
        krs_v = krs[krs["KR_ID"].isin(kr_ids)] if kr_ids else krs.iloc[0:0]
        acoes_v = acoes[acoes["KR_ID_USADA"].isin(kr_ids)] if kr_ids else acoes.iloc[0:0]
        kpis_v = kpis[kpis["KPI_ID"] == sel_kpi]
        return okrs_v, krs_v, acoes_v, kpis_v

    if sel_kr:
        okr_id = kr_to_okr.get(sel_kr, "")
        okrs_v = okrs[okrs["OKR_ID"] == okr_id] if okr_id else okrs
        krs_v = krs[krs["KR_ID"] == sel_kr]
        acoes_v = acoes[acoes["KR_ID_USADA"] == sel_kr]
        kpi_ids = okr_kpi[okr_kpi["KR_ID"] == sel_kr]["KPI_ID"].unique().tolist()
        kpis_v = kpis[kpis["KPI_ID"].isin(kpi_ids)] if kpi_ids else kpis.iloc[0:0]
        return okrs_v, krs_v, acoes_v, kpis_v

    if sel_okr:
        okrs_v = okrs[okrs["OKR_ID"] == sel_okr]
        krs_v = krs[krs["OKR_ID"] == sel_okr]
        acoes_v = acoes[acoes["OKR_USED"] == sel_okr]
        kpi_ids = okr_kpi[okr_kpi["OKR_ID"] == sel_okr]["KPI_ID"].unique().tolist()
        kpis_v = kpis[kpis["KPI_ID"].isin(kpi_ids)] if kpi_ids else kpis.iloc[0:0]
        return okrs_v, krs_v, acoes_v, kpis_v

    return okrs, krs, acoes, kpis

# ────────────────────────────────────────────────
#   Sidebar
# ────────────────────────────────────────────────
with st.sidebar:
    uploaded = st.file_uploader("Planilha (.xlsx)", type=["xlsx"])
    file_path = FILE_DEFAULT if uploaded is None else uploaded

    st.divider()
    st.caption(f"Layout: {LAYOUT_FILE}")
    if st.button("Recarregar layout JSON", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    if st.button("Limpar todas as seleções", use_container_width=True, type="primary"):
        for k in ["sel_okr", "sel_kr", "sel_acao", "sel_kpi"]:
            st.session_state[k] = None
        st.rerun()

# ────────────────────────────────────────────────
#   Load + selections
# ────────────────────────────────────────────────
layout_cfg = load_layout(LAYOUT_FILE)
global_labels = (layout_cfg.get("__global__", {}) or {}).get("labels", {}) or {}

okrs, krs, kpis, okr_kpi, acoes = load_data(file_path)
for k in ["sel_okr", "sel_kr", "sel_acao", "sel_kpi"]:
    st.session_state.setdefault(k, None)

# KPI -> OKRs (comma-separated)
kpi_to_okrs = (
    okr_kpi.groupby("KPI_ID")["OKR_ID"]
    .apply(lambda s: ", ".join(sorted({str(x).strip() for x in s if str(x).strip() not in ("", "nan", "None")})))
    .to_dict()
)
kpis = kpis.copy()
kpis["OKRs_relacionadas"] = kpis["KPI_ID"].map(lambda k: kpi_to_okrs.get(str(k).strip(), ""))

okrs_v, krs_v, acoes_v, kpis_v = filter_views(
    okrs, krs, kpis, okr_kpi, acoes,
    sel_okr=st.session_state.sel_okr,
    sel_kr=st.session_state.sel_kr,
    sel_acao=st.session_state.sel_acao,
    sel_kpi=st.session_state.sel_kpi,
)

# ────────────────────────────────────────────────
#   Header with logo (top-right)
# ────────────────────────────────────────────────
left, right = st.columns([9, 1])
with left:
    st.title("OKRs • KRs • Ações • KPIs")
with right:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=90)

st.markdown("### Monitoramento da execução do Planejamento Estratégico")

# ────────────────────────────────────────────────
#   Dashboard
# ────────────────────────────────────────────────
acoes_dash = acoes.copy()
if "STATUS" not in acoes_dash.columns:
    acoes_dash["STATUS"] = "Sem status"
acoes_dash["STATUS"] = acoes_dash["STATUS"].astype(str).str.strip()

def norm_status(s: str) -> str:
    t = (s or "").lower()
    if "concl" in t or "final" in t or "done" in t:
        return "Concluída"
    if "andam" in t or "execu" in t or "prog" in t or t.startswith("em "):
        return "Em andamento"
    if "pend" in t or "a fazer" in t or "todo" in t:
        return "Pendente"
    return s if s else "Sem status"

acoes_dash["STATUS_N"] = acoes_dash["STATUS"].map(norm_status)
acoes_dash["OKR_USED"] = acoes_dash.get("OKR_USED", "").astype(str).str.strip().replace({"nan": ""})

dash = (
    acoes_dash[acoes_dash["OKR_USED"] != ""]
    .groupby(["OKR_USED", "STATUS_N"], as_index=False)
    .size()
    .rename(columns={"size": "Qtd"})
)

if dash.empty:
    st.info("Não encontrei ações com OKR_USED preenchido para montar o dashboard.")
else:
    total = int(dash["Qtd"].sum())
    pend = int(dash.loc[dash["STATUS_N"] == "Pendente", "Qtd"].sum())
    anda = int(dash.loc[dash["STATUS_N"] == "Em andamento", "Qtd"].sum())
    conc = int(dash.loc[dash["STATUS_N"] == "Concluída", "Qtd"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ações (total)", total)
    c2.metric("Pendente", pend)
    c3.metric("Em andamento", anda)
    c4.metric("Concluída", conc)

    st.markdown("#### Ações por OKR e Status (barra empilhada)")
    chart = (
        alt.Chart(dash)
        .mark_bar()
        .encode(
            x=alt.X("OKR_USED:N", title="OKR"),
            y=alt.Y("Qtd:Q", title="Quantidade de ações"),
            color=alt.Color("STATUS_N:N", title="Status"),
            tooltip=["OKR_USED", "STATUS_N", "Qtd"],
        )
    )
    st.altair_chart(chart, use_container_width=True)

st.markdown("### Clique na linha desejada para fixar o filtro (clique novamente para remover)")

# ────────────────────────────────────────────────
#   Tables
# ────────────────────────────────────────────────
def selectable_table(df: pd.DataFrame, id_col: str, title: str, session_key: str, layout_key: str):
    st.subheader(title)
    if df.empty:
        st.info("Nenhum registro após os filtros atuais.")
        return

    df = df.copy()
    if "_selected" not in df.columns:
        df["_selected"] = False

    current_sel = st.session_state.get(session_key)
    if current_sel is not None and id_col in df.columns:
        df["_selected"] = df[id_col].astype(str) == str(current_sel)

    layout = layout_cfg.get(layout_key, {"order": [], "width": {}, "labels": {}}) or {}
    order = layout.get("order", []) or []
    if order:
        df = _apply_order_and_hide(df, order)

    width_map = layout.get("width", {}) or {}
    labels_map = layout.get("labels", {}) or {}
    col_cfg = build_column_config(df, width_map, labels_map, global_labels, default_width="medium")

    st.data_editor(
        df,
        column_config=col_cfg,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        key=f"editor_{session_key}",
    )

    changes = st.session_state.get(f"editor_{session_key}", {})
    if isinstance(changes, dict) and changes.get("edited_rows"):
        for row_idx, edits in changes["edited_rows"].items():
            if "_selected" in edits:
                new_value = edits["_selected"]
                selected_id = str(df.iloc[int(row_idx)][id_col])

                if new_value is True:
                    st.session_state[session_key] = selected_id
                    for other in ["sel_okr", "sel_kr", "sel_acao", "sel_kpi"]:
                        if other != session_key:
                            st.session_state[other] = None
                else:
                    if st.session_state.get(session_key) == selected_id:
                        st.session_state[session_key] = None

                st.rerun()
                break

# OKRs
okrs_df = okrs_v[["OKR_ID", "Eixo_CAPES", okrs_v.columns[-1]]].rename(columns={okrs_v.columns[-1]: "Objetivo_OKR"})
selectable_table(okrs_df, "OKR_ID", "**OKRs**", "sel_okr", "okrs")

# KRs
krs_df = krs_v[["KR_ID", "OKR_ID", "Resultado-chave", "Meta_2028", "Frequência"]]
selectable_table(krs_df, "KR_ID", "**KRs**", "sel_kr", "krs")

# Ações
acoes_cols = ["ID", "EIXO", "O QUÊ?", "STATUS", "OKR_USED", "KR_ID_USADA"]
acoes_show = acoes_v[acoes_cols] if all(c in acoes_v.columns for c in acoes_cols) else acoes_v
selectable_table(acoes_show, "ID", "**Ações**", "sel_acao", "acoes")

# KPIs
kpi_cols = ["KPI_ID", "KPI", "OKRs_relacionadas", "Unidade", "Frequência", "Fonte"]
kpis_show = kpis_v[kpi_cols] if all(c in kpis_v.columns for c in kpi_cols) else kpis_v
selectable_table(kpis_show, "KPI_ID", "**KPIs**", "sel_kpi", "kpis")

st.caption("Dica: clique novamente na linha selecionada (checkbox) para remover o filtro.")