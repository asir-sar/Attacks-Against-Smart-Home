import subprocess
import streamlit as st
import shlex

def run_command(command_list):
    """
    Executes a system command and streams the output to Streamlit.
    Args:
        command_list (list): A list of strings, e.g., ["nmap", "-sV", "192.168.1.1"]
    """
    # Create a placeholder for real-time logs
    output_container = st.empty()
    full_output = []

    try:
        # Popen allows us to read stdout in real-time
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Iterate over output lines as they are generated
        with output_container.container():
            st.info(f"🚀 Executing: {' '.join(command_list)}")
            code_block = st.empty()
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    full_output.append(line)
                    # Update the code block with the latest 20 lines to keep it readable
                    code_block.code("\n".join(full_output[-20:]), language="bash")

        # Wait for process to finish
        process.wait()
        
        if process.returncode == 0:
            st.success("✅ Attack/Scan Completed Successfully")
            # Show full log in an expander
            with st.expander("View Full Log"):
                st.code("\n".join(full_output))
        else:
            stderr = process.stderr.read()
            st.error(f"❌ Process failed with return code {process.returncode}")
            st.error(stderr)

    except FileNotFoundError:
        st.error(f"❌ Error: The tool '{command_list[0]}' is not installed or not found in PATH.")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {str(e)}")
