# SmartService Chat UI — 基于 Streamlit 的演示界面

import streamlit as st
import requests
import json
import time
import uuid
import os

# ─── 配置 ────────────────────────────────────────────
API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")
API_KEY = os.getenv("API_KEY", "sk-demo-key")

st.set_page_config(
    page_title="SmartService 智能客服",
    page_icon="",
    layout="wide",
)

# ─── 侧边栏 ──────────────────────────────────────────
with st.sidebar:
    st.title(" SmartService")
    st.markdown("**智能客服多Agent协同平台**")
    st.divider()

    # 意图显示
    if "last_intent" in st.session_state:
        intent = st.session_state.last_intent
        intent_name = intent.get("intent", "unknown") if isinstance(intent, dict) else str(intent)
        confidence = intent.get("confidence", 0) if isinstance(intent, dict) else 0
        st.metric("意图", intent_name)
        st.metric("置信度", f"{confidence:.0%}")

    st.divider()
    st.caption("v1.0.0 | Powered by LangGraph + Qwen")

    if st.button("🔄 新对话"):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()

# ─── 会话初始化 ──────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# ─── 欢迎消息 ────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    ## 您好，我是 SmartService 智能客服

    我可以帮您：
    - 💬 **回答产品使用、退换货政策等问题**
    - 📦 **查询订单状态和物流信息**
    - 👤 **查询会员等级和积分**
    - 🔄 **需要时自动转接人工客服**

    请直接输入您的问题开始吧！
    """)

# ─── 对话历史 ────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("trace"):
            with st.expander("🔍 Agent 调用链"):
                st.json(msg["trace"], expanded=False)

# ─── 用户输入 ────────────────────────────────────────
if prompt := st.chat_input("输入您的问题..."):
    # 显示用户消息
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用 API
    with st.chat_message("assistant"):
        with st.spinner("Agent 思考中..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/chat/send-sync",
                    json={
                        "conversation_id": st.session_state.session_id,
                        "message": prompt,
                    },
                    headers={"X-API-Key": API_KEY},
                    timeout=60,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "抱歉，系统暂时无法处理。")
                    st.markdown(response_text)

                    # 显示调用链
                    trace = {
                        "trace_id": data.get("trace_id"),
                        "intent": str(data.get("intent")),
                        "confidence": data.get("confidence"),
                        "tool_calls": data.get("tool_calls"),
                        "latency_ms": data.get("total_latency_ms"),
                        "tokens": data.get("total_tokens"),
                    }
                    with st.expander("🔍 Agent 调用链"):
                        st.json(trace, expanded=False)

                    # 保存状态
                    st.session_state.session_id = data.get("session_id")
                    st.session_state.last_intent = trace["intent"]
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "trace": trace,
                    })
                else:
                    st.error(f"API 错误: {resp.status_code}")
            except requests.ConnectionError:
                st.error(" 无法连接到后端服务，请确保 FastAPI 已启动 (localhost:8000)")
            except Exception as e:
                st.error(f"请求失败: {e}")
