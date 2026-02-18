import streamlit as st
import requests
import json
from typing import Optional

# Page config
st.set_page_config(
    page_title="🚗 ПДД AI Казахстан",
    page_icon="🚗",
    layout="wide"
)

# Styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 20px;
    }
    .answer-box {
        background-color: #f0f4f8;
        padding: 20px;
        border-left: 4px solid #4CAF50;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 20px;
        border-left: 4px solid #ff9800;
        border-radius: 5px;
        margin: 10px 0;
    }
    .source-box {
        background-color: #e3f2fd;
        padding: 10px;
        border-left: 4px solid #2196F3;
        border-radius: 5px;
        margin: 5px 0;
        font-size: 12px;
    }
    .confidence {
        font-size: 12px;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🚗 ПДД AI Казахстан</h1>
    <p>Справочный сервис по правилам дорожного движения</p>
    <p style="color: #999; font-size: 12px;">⚠️ Информационный сервис, не является юридической консультацией</p>
</div>
""", unsafe_allow_html=True)

# Backend URL (configurable)
try:
    BACKEND_URL = st.secrets.get("backend_url", "http://localhost:8000")
except (FileNotFoundError, KeyError, AttributeError):
    BACKEND_URL = "http://localhost:8000"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Настройки")
    
    backend_url = st.text_input(
        "Backend URL",
        value=BACKEND_URL,
        help="Адрес серверной части приложения"
    )
    
    language = st.selectbox(
        "Язык",
        ["🇷🇺 Русский", "🇰🇿 Қазақша"],
        index=0
    )
    
    st.divider()
    st.markdown("### 📖 Часто задаваемые вопросы")
    
    sample_questions = {
        "Кто уступает на круге?": "circle",
        "Какой штраф за красный?": "red_light",
        "Правила обгона": "overtaking",
        "Скорость в городе": "speed",
    }
    
    for question, key in sample_questions.items():
        if st.button(f"❓ {question}", key=key):
            st.session_state.current_question = question

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🤔 Задайте вопрос по ПДД")
    
    # Question input
    current_question = st.session_state.get("current_question", "")
    question = st.text_area(
        "Ваш вопрос",
        value=current_question,
        placeholder="Например: Могу ли я обгонять на пешеходном переходе?",
        height=100,
        label_visibility="collapsed"
    )
    
    # Clear the session state variable
    if "current_question" in st.session_state:
        del st.session_state.current_question
    
    col_ask, col_clear = st.columns(2)
    
    with col_ask:
        ask_button = st.button("🔍 Спросить", type="primary", use_container_width=True)
    
    with col_clear:
        if st.button("🗑️ Очистить", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Submit question
    if ask_button and question:
        st.session_state.messages.append({"role": "user", "question": question})
        
        # Show loading spinner
        with st.spinner("⏳ Ищу информацию в ПДД..."):
            try:
                response = requests.post(
                    f"{backend_url}/ask",
                    json={
                        "question": question,
                        "language": "ru"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "answer": data.get("answer", ""),
                        "sources": data.get("sources", []),
                        "confidence": data.get("confidence", 0)
                    })
                    st.success("✅ Ответ получен!")
                    st.rerun()
                else:
                    st.error(f"❌ Ошибка сервера: {response.status_code}")
                    st.error(response.text)
                    
            except requests.exceptions.ConnectionError:
                st.error(f"""❌ Не могу подключиться к серверу.

Проверьте что backend запущен:
- Backend URL: {backend_url}
- Должен быть запущен на порту 8000

Запустите в терминале:
```bash
cd backend
py -3.12 main.py
```
""")
            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")
                st.error(f"Backend URL: {backend_url}")
    
    st.divider()
    
    # Display conversation
    st.markdown("### 💬 История диалога")
    
    if not st.session_state.messages:
        st.info("👆 Задайте вопрос чтобы начать")
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["question"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["answer"])
                    
                    # Display sources
                    if msg.get("sources"):
                        st.markdown("**📋 Источники:**")
                        for source in msg["sources"]:
                            st.markdown(f"""
<div class="source-box">
    <b>{source.get('section', 'Unknown')}</b><br>
    {source.get('title', '')}<br>
    <span class="confidence">Релевантность: {source.get('relevance', 0):.0%}</span>
</div>
""", unsafe_allow_html=True)
                    
                    # Display confidence
                    confidence = msg.get("confidence", 0)
                    col_conf, col_warn = st.columns([2, 3])
                    
                    with col_conf:
                        st.markdown(f"<div class='confidence'>Уверенность: {confidence:.0%}</div>", unsafe_allow_html=True)
                    
                    if confidence < 0.5:
                        with col_warn:
                            st.warning("⚠️ Низкая уверенность - проверьте информацию")
                    
                    st.divider()

# Footer
with col2:
    st.markdown("""
### ℹ️ О сервисе

**ПДД AI Казахстан** - справочный сервис на основе искусственного интеллекта для ответов на вопросы о правилах дорожного движения Республики Казахстан.

### ⚠️ Важно!

- Это **информационный сервис**, не юридическая консультация
- БЕЗ ИИН и персональных данных
- Проверяйте информацию по официальным источникам
- При ДТП обратитесь в МВД

### 📚 Источники

- Правила дорожного движения РК
- Административный кодекс РК

### 🔗 Контакты

- GitHub: [roadlaw-ai](https://github.com)
- Обратная связь: support@roadlaw.kz
""")

