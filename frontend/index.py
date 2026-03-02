import streamlit as st
import requests
import uuid

API_BASE = "http://localhost:8000/api"

st.set_page_config(page_title="Atome Customer Service System", layout="wide")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages =[]

with st.sidebar:
    st.title("🛠️ Manager Dashboard")
    st.markdown("You can edit the bot configuration here and it will take effect immediately.")
    
    try:
        config_res = requests.get(f"{API_BASE}/config").json()
        current_url = config_res.get("kb_url", "")
        current_guidelines = config_res.get("guidelines", "")
    except:
        current_url, current_guidelines = "", ""

    with st.form("config_form"):
        new_url = st.text_input("Knowledge Base URL", value=current_url)
        new_guidelines = st.text_area("Additional Guidelines", value=current_guidelines, height=150)
        submitted = st.form_submit_button("Update Bot Configuration")
        
        if submitted:
            with st.spinner("Updating Bot... (If URL changed, parsing may take a few seconds)"):
                res = requests.post(
                    f"{API_BASE}/config", 
                    json={"kb_url": new_url, "guidelines": new_guidelines}
                )
                if res.status_code == 200:
                    st.success("✅ Bot has been updated successfully!")
                else:
                    st.error("❌ Failed to update Bot.")

st.title("💬 Atome Customer Service")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything about Atome..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    f"{API_BASE}/chat",
                    json={"message": prompt, "session_id": st.session_state.session_id}
                ).json()
                reply = res.get("reply", "Error communicating with backend.")
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Backend error: {e}")