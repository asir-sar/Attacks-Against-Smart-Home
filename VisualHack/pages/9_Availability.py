import streamlit as st
import subprocess
import time
import requests
import pandas as pd
from utils import run_command

st.set_page_config(page_title="Availability Check", page_icon="📉")

st.header("📉 Availability & Stress Testing")
st.markdown("Check if a target is alive (Ping) or test its response under load (HTTP Stress).")

# Tabs for different methods
tab1, tab2 = st.tabs(["📡 ICMP Ping", "🔥 HTTP Stress Test"])

# --- TAB 1: SYSTEM PING ---
with tab1:
    st.subheader("ICMP Echo Request")
    
    ping_target = st.text_input("Target IP", "192.168.1.15", key="ping_ip")
    ping_count = st.slider("Count", 1, 50, 4)
    
    if st.button("Run Ping"):
        # Linux ping syntax: ping -c <count> <ip>
        command = ["ping", "-c", str(ping_count), ping_target]
        run_command(command)

# --- TAB 2: HTTP STRESS ---
with tab2:
    st.subheader("HTTP Response Monitor")
    
    http_target = st.text_input("Target URL", "http://192.168.1.15:80", key="http_url")
    num_requests = st.slider("Number of Requests", 5, 100, 10)
    delay = st.slider("Delay between requests (sec)", 0.0, 2.0, 0.1)
    
    if st.button("🚀 Start Stress Test"):
        st.info(f"Sending {num_requests} requests to {http_target}...")
        
        results = []
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        for i in range(num_requests):
            try:
                start_t = time.time()
                r = requests.get(http_target, timeout=2)
                latency = (time.time() - start_t) * 1000
                
                status_code = r.status_code
                status = "✅ Up" if status_code == 200 else f"⚠️ {status_code}"
                
            except Exception as e:
                latency = 0
                status_code = 0
                status = "❌ Down"
            
            # Record Data
            results.append({
                "Request": i+1,
                "Status": status,
                "Code": status_code,
                "Latency (ms)": round(latency, 2)
            })
            
            # Update UI
            progress_bar.progress((i + 1) / num_requests)
            status_area.text(f"Request {i+1}/{num_requests}: {status} ({round(latency,2)}ms)")
            time.sleep(delay)
            
        # Display Results
        df = pd.DataFrame(results)
        st.dataframe(df)
        
        # Simple Chart
        if "Latency (ms)" in df.columns:
            st.line_chart(df["Latency (ms)"])
