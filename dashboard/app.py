from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_URL = os.getenv("LOFIN_API_URL", "http://localhost:8000")

st.set_page_config(page_title="LoFin Intelligence", layout="wide")
st.title("LoFin Multi-Agent Financial Intelligence")
st.caption("Local-first longitudinal monitoring for stocks, ETFs, narratives, sentiment, and options mentions.")


def get(path: str):
    response = requests.get(f"{API_URL}{path}", timeout=20)
    response.raise_for_status()
    return response.json()


with st.sidebar:
    st.header("Controls")
    ticker = st.text_input("Ticker / ETF", "NVDA")
    if st.button("Run local analysis cycle"):
        resp = requests.post(f"{API_URL}/analyze", json={"source": "all", "limit": 25}, timeout=180)
        st.write(resp.json())
    if st.button("Apply retention cleanup"):
        resp = requests.post(f"{API_URL}/cleanup", json={}, timeout=60)
        st.write(resp.json())

col1, col2 = st.columns(2)
with col1:
    st.subheader("Top Discussed Stocks")
    stocks = pd.DataFrame(get("/top-tickers"))
    st.dataframe(stocks, use_container_width=True)
    if not stocks.empty:
        st.plotly_chart(px.bar(stocks, x="symbol", y="mentions", color="confidence"), use_container_width=True)
with col2:
    st.subheader("Top Discussed ETFs")
    etfs = pd.DataFrame(get("/top-etfs"))
    st.dataframe(etfs, use_container_width=True)
    if not etfs.empty:
        st.plotly_chart(px.bar(etfs, x="symbol", y="mentions", color="confidence"), use_container_width=True)

st.subheader(f"{ticker.upper()} Longitudinal Profile")
profile = get(f"/ticker/{ticker.upper()}")
st.json(profile)

st.subheader("Narrative Clusters")
narratives = pd.DataFrame(get("/narratives"))
st.dataframe(narratives, use_container_width=True)
if not narratives.empty:
    st.plotly_chart(px.scatter(narratives, x="first_seen_at", y="velocity", size="mention_count", color="theme", hover_data=["title", "symbols"]), use_container_width=True)

st.subheader("Daily AI Summaries")
for summary in get("/summary/daily"):
    with st.expander(f"{summary['date']} · {summary['scope']} · confidence {summary['confidence']:.2f}"):
        st.write(summary["content"])
        st.write("Catalysts", summary["catalysts"])
        st.write("Risks", summary["risks"])
