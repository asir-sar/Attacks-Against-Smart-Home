import streamlit as st
import os
import sys

st.set_page_config(
    page_title="Kali Attack Dashboard", 
    page_icon="💀", 
    layout="wide"
)

st.title("💀 Automated Attack Dashboard")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.write("### Status Panel")
    # Check Root Privileges
    if os.geteuid() != 0:
        st.error("⚠️ Root privileges missing! Run with `sudo streamlit run app.py`")
    else:
        st.success("✅ Running as Root (Privileged)")

    # Check Python Version
    st.info(f"🐍 Python Environment: {sys.version.split()[0]}")

with col2:
    st.write("### Instructions")
    st.info("👈 Select a module from the sidebar to start an operation.")
    st.warning("Only use this tool on systems you have explicit permission to test.")
