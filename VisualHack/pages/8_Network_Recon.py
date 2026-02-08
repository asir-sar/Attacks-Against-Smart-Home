import streamlit as st
import shutil
import re
from utils import run_command

st.set_page_config(page_title="Network Recon", page_icon="🌐")

st.header("🌐 Network Reconnaissance (Nmap)")
st.markdown("This module uses **Nmap** to discover hosts and services on the network.")

# --- CHECK DEPENDENCY ---
if shutil.which("nmap") is None:
    st.error("❌ 'nmap' is not installed. Please run: `sudo apt install nmap`")
    st.stop()

# --- INPUT SECTION ---
col1, col2 = st.columns(2)

with col1:
    target_ip = st.text_input("Target IP / Subnet", value="192.168.1.1/24", help="e.g., 192.168.1.15 or 192.168.1.0/24")
    
with col2:
    scan_profile = st.selectbox("Scan Profile", [
        "Quick Scan (-F)",
        "Service Version (-sV)",
        "Aggressive Scan (-A)",
        "OS Detection (-O)",
        "All Ports (-p-)"
    ])

# Advanced Options
with st.expander("Advanced Options"):
    output_file = st.checkbox("Save output to file?")
    filename = st.text_input("Filename", "scan_results.txt") if output_file else None
    no_ping = st.checkbox("Skip Ping (-Pn)", value=True, help="Useful if target blocks ICMP")

# --- EXECUTION LOGIC ---
if st.button("🚀 Launch Scan"):
    if not target_ip:
        st.error("Please enter a target IP.")
        st.stop()
    
    # Construct the command list
    command = ["nmap"]
    
    # Add profile flags
    if "Quick" in scan_profile:
        command.append("-F")
    elif "Version" in scan_profile:
        command.append("-sV")
    elif "Aggressive" in scan_profile:
        command.append("-A")
    elif "OS" in scan_profile:
        command.append("-O")
    elif "All Ports" in scan_profile:
        command.append("-p-")
    
    # Add optional flags
    if no_ping:
        command.append("-Pn")
        
    if output_file and filename:
        command.extend(["-oN", filename])
        
    # Add target
    command.append(target_ip)
    
    # Run
    run_command(command)
