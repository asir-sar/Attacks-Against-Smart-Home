import streamlit as st
import requests
import time
import os

st.set_page_config(page_title="Directory Buster", page_icon="🔍")

st.header("🔍 Directory & File Fuzzer")
st.markdown("This module performs **Enumeration**. It blindly attempts to access common filenames and directories to find hidden assets on the target web server.")

# --- INPUT CONFIGURATION ---
col1, col2 = st.columns(2)

with col1:
    target_url = st.text_input("Target Base URL", "http://192.168.88.252:3001/")
    # Ensure URL ends with a slash
    if not target_url.endswith("/"):
        target_url += "/"

with col2:
    wordlist_mode = st.radio("Wordlist Source", ["Quick Demo List (Fast)", "Custom Wordlist File"])
    
    custom_path = ""
    if wordlist_mode == "Custom Wordlist File":
        custom_path = st.text_input("Path to Wordlist", "/usr/share/wordlists/dirb/common.txt")

# --- EXECUTION ---
if st.button("🚀 Start Enumeration"):
    st.info(f"Scanning target: {target_url}")
    
    # 1. Define the Wordlist
    words = []
    
    if wordlist_mode == "Quick Demo List (Fast)":
        # A curated list of likely suspects for your project
        words = [
            "admin", "login", "dashboard", 
            "logs", "system", "backup", 
            "config", "robot.txt", "sitemap.xml",
            "system_logs.json", "database.db", "users.sql",
            "secrets", "env", ".env", "api"
        ]
        st.caption("Loaded built-in demo list (15 items).")
        
    else:
        # Load from file
        if os.path.exists(custom_path):
            try:
                with open(custom_path, "r", encoding="utf-8", errors="ignore") as f:
                    words = [line.strip() for line in f if line.strip()]
                st.caption(f"Loaded {len(words)} words from {custom_path}.")
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.stop()
        else:
            st.error("Wordlist file not found.")
            st.stop()

    # 2. The Scanner Loop
    found_assets = []
    
    # Create UI elements for progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_area = st.container()
    
    # We use a session state variable to allow stopping? 
    # (Streamlit loop is hard to stop cleanly without complex logic, 
    # so we will just run through the list)
    
    total = len(words)
    
    for i, word in enumerate(words):
        # Construct full URL
        full_url = f"{target_url}{word}"
        
        try:
            # Send Request
            # We assume a 5-second timeout
            r = requests.get(full_url, timeout=2, allow_redirects=False)
            
            code = r.status_code
            
            # Logic: What counts as "Found"?
            # Usually 200 (OK), 301/302 (Redirect), 403 (Forbidden - usually means it exists but is locked)
            if code in [200, 301, 302, 401, 403]:
                found_assets.append({
                    "Path": f"/{word}",
                    "Status": code,
                    "Full URL": full_url
                })
                
                # Show immediately in the UI
                with results_area:
                    if code == 200:
                        st.success(f"✅ FOUND: /{word} (200 OK)")
                    elif code == 403:
                        st.warning(f"🔒 LOCKED: /{word} (403 Forbidden)")
                    else:
                        st.info(f"➡️ REDIRECT: /{word} ({code})")
            
            # Update status (Optional: show current word being tested)
            # status_text.text(f"Testing: /{word}")
            
        except requests.exceptions.RequestException:
            pass # Ignore connection errors (host down or timeout)
        
        # Update Progress
        progress_bar.progress((i + 1) / total)
        
        # Small sleep only for demo mode to make it look cool/readable
        # Remove this if using a real huge wordlist!
        if wordlist_mode == "Quick Demo List (Fast)":
            time.sleep(0.1)

    st.success("🏁 Scan Complete.")
    
    # Summary Table
    if found_assets:
        st.write("### 📝 Discovery Summary")
        st.dataframe(found_assets)
        st.markdown("💡 **Next Step:** Copy the **Full URL** of any interesting file (like `system_logs.json`) and paste it into the **Data Exfiltration** module.")
    else:
        st.warning("No assets found in this wordlist.")
