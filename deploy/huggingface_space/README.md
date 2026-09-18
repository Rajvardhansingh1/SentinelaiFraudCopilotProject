---
title: SentinelAI Fraud Copilot
emoji: 🛡️
colorFrom: blue
colorTo: gray
sdk: streamlit
sdk_version: "1.64.0"
app_file: frontend/app.py
pinned: false
---

# SentinelAI + Fraud Copilot — Demo

Public demo of the SentinelAI proxy + Fraud Copilot playground/review UI.

Set `PROXY_BASE_URL` in this Space's Settings → Variables and secrets to point at the
deployed Render proxy (e.g. `https://sentinelai-proxy.onrender.com`). Falls back to
`http://localhost:8000` if unset.
