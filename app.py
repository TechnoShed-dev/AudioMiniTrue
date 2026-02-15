# ------------------------------------------------------------------------------
# Project:      Minitrue
# Filename:     app.py
# Version:      v0.11.0
# Author:       Karl @ TechnoShed
# Date:         2026-02-15
# Website:      https://technoshed.co.uk
# Description:  Streamlit interface for rewriting MP3 history.
#               Added: Bulk Editing (Fill Down, Set All, Smart Fill).
#               *** SIMULATION MODE ACTIVE ***
# ------------------------------------------------------------------------------

import streamlit as st
import os
import pandas as pd
import re
from mutagen.easyid3 import EasyID3
import mutagen

# --- Config ---
st.set_page_config(page_title="Minitrue (TEST MODE)", layout="wide", page_icon="📻")
ROOT_DIR = "/music"
LIBRARY_DIR = os.path.join(ROOT_DIR, "Library")
PROTECTED_FOLDERS = ["jingles", "adverts", "station_ids", "sweepers", "news", "ftp_upload"]

# --- CSS INJECTION (Slim Sidebar) ---
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            min-width: 180px;
            max-width: 220px;
        }
        .block-container {
            padding-top: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Session State ---
if 'current_path' not in st.session_state:
    st.session_state.current_path = ROOT_DIR
if 'df_editor' not in st.session_state:
    st.session_state.df_editor = None

# --- Helper Functions ---
def sanitize_name(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

def get_files_in_directory(path):
    try:
        items = os.listdir(path)
        dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
        files = [f for f in items if f.lower().endswith('.mp3')]
        dirs.sort()
        files.sort()
        return dirs, files
    except Exception as e:
        st.error(f"Error accessing path: {e}")
        return [], []

def get_mp3_tags(file_path):
    try:
        audio = EasyID3(file_path)
        return {
            "Artist": audio.get('artist', [''])[0],
            "Album": audio.get('album', [''])[0],
            "Title": audio.get('title', [''])[0],
            "File": os.path.basename(file_path),
            "Full Path": file_path,
            "Status": "Pending"
        }
    except mutagen.id3.ID3NoHeaderError:
        return {"Artist": "", "Album": "", "Title": "", "File": os.path.basename(file_path), "Full Path": file_path, "Status": "No Tags"}
    except Exception:
        return {"Artist": "", "Album": "", "Title": "", "File": os.path.basename(file_path), "Full Path": file_path, "Status": "Error"}

def process_file_dry_run(row):
    src_path = row['Full Path']
    artist = sanitize_name(row['Artist'])
    album = sanitize_name(row['Album'])
    title = sanitize_name(row['Title'])
    
    if not artist or not title:
        return "❌ Skip: Missing Artist/Title"
    
    for p in PROTECTED_FOLDERS:
        if f"/{p}/" in src_path or src_path.endswith(f"/{p}"):
            return f"🛡️ Protected ({p})"

    target_album = album if album else "Radio_Uploads"
    return f"✅ /Library/{artist}/{target_album}/{title}.mp3"

def clean_radio_filename(filename, operation):
    base = os.path.splitext(filename)[0]
    if operation == "Strip Numeric Prefix (1001_...)":
        base = re.sub(r'^\d+_+', '', base)
    elif operation == "Underscores to Spaces":
        base = base.replace("_", " ")
    elif operation == "Title Case":
        base = base.title()
    elif operation == "Smart Space (Session001 -> Session 001)":
        base = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', base)
        base = base[0].upper() + base[1:] if base else base
    return base

# --- UI Layout ---
with st.sidebar:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", use_container_width=True)
    st.markdown("### Nav")
    if st.button("🏠 Root"):
        st.session_state.current_path = ROOT_DIR
        st.rerun()
    st.caption(f"📂 ...{st.session_state.current_path[-20:]}" if len(st.session_state.current_path) > 20 else st.session_state.current_path)

st.title("📻 Minitrue: Bulk Editor")
st.caption(f"v0.11.0 | TechnoShed | Slim Layout")

col1, col2 = st.columns([1, 6])
with col1:
    if st.session_state.current_path != ROOT_DIR:
        if st.button("⬅️ Up"):
            st.session_state.current_path = os.path.dirname(st.session_state.current_path)
            st.rerun()

dirs, files = get_files_in_directory(st.session_state.current_path)

if dirs:
    st.write("### Subfolders")
    cols = st.columns(5)
    for i, d in enumerate(dirs):
        label = f"📁 {d}"
        if d.lower() in PROTECTED_FOLDERS:
            label = f"🛡️ {d}"
        if cols[i % 5].button(label, key=f"dir_{d}_{i}"):
            st.session_state.current_path = os.path.join(st.session_state.current_path, d)
            st.rerun()

st.divider()
st.subheader(f"🎵 Editing: {os.path.basename(st.session_state.current_path)}")

if files:
    if st.button("🔄 Load/Refresh Files"):
        tag_data = []
        for f in files:
            full_path = os.path.join(st.session_state.current_path, f)
            tag_data.append(get_mp3_tags(full_path))
        st.session_state.df_editor = pd.DataFrame(tag_data)

    if st.session_state.df_editor is not None and not st.session_state.df_editor.empty:
        
        # --- BULK EDIT TOOLS ---
        with st.expander("🛠️ Bulk Edit & Fill Tools", expanded=True):
            b_col1, b_col2, b_col3 = st.columns(3)
            
            with b_col1:
                st.markdown("**1. Fill Down**")
                st.caption("Fills empty 'Artist' cells using the value from the row above.")
                if st.button("⬇️ Fill Down Artists"):
                    df = st.session_state.df_editor
                    # Forward fill propagates the last valid observation forward
                    df['Artist'] = df['Artist'].replace('', pd.NA).ffill().fillna('')
                    st.session_state.df_editor = df
                    st.success("Filled down!")
                    st.rerun()

            with b_col2:
                st.markdown("**2. Set All**")
                st.caption("Sets 'Artist' for EVERY row to this value.")
                bulk_artist = st.text_input("Artist Name", placeholder="e.g. TechnoShed Radio")
                if st.button("Apply to All Rows"):
                    if bulk_artist:
                        df = st.session_state.df_editor
                        df['Artist'] = bulk_artist
                        st.session_state.df_editor = df
                        st.success(f"All artists set to '{bulk_artist}'!")
                        st.rerun()

            with b_col3:
                st.markdown("**3. Smart Guess**")
                st.caption("Fills blanks with the most common Artist in this folder.")
                if st.button("✨ Auto-Fill Blanks"):
                    df = st.session_state.df_editor
                    # Find mode (most common value) excluding empty strings
                    valid_artists = df[df['Artist'] != '']['Artist']
                    if not valid_artists.empty:
                        common_artist = valid_artists.mode()[0]
                        # Only fill blanks
                        df['Artist'] = df['Artist'].apply(lambda x: common_artist if x == '' else x)
                        st.session_state.df_editor = df
                        st.success(f"Blanks filled with '{common_artist}'")
                        st.rerun()
                    else:
                        st.warning("No artists found to guess from!")

        # --- TABS ---
        tab_clean, tab_parse = st.tabs(["🧹 Smart Cleaner", "📝 Tag Parser"])
        
        with tab_clean:
            clean_op = st.selectbox("Operation", [
                "Smart Space (Session001 -> Session 001)",
                "Strip Numeric Prefix (1001_...)",
                "Underscores to Spaces",
                "Title Case"
            ])
            if st.button("Apply to Filename Column"):
                df = st.session_state.df_editor
                df['File'] = df['File'].apply(lambda x: clean_radio_filename(x, clean_op) + ".mp3")
                st.session_state.df_editor = df
                st.success("Filenames updated!")
                st.rerun()

        with tab_parse:
            parse_mode = st.radio("Pattern Type", ["Title Only (Use whole filename)", "Artist - Title"], horizontal=True)
            if st.button("Apply Tags"):
                df = st.session_state.df_editor
                for idx, row in df.iterrows():
                    base = os.path.splitext(row['File'])[0]
                    if parse_mode == "Title Only (Use whole filename)":
                        df.at[idx, 'Title'] = base.strip()
                    elif parse_mode == "Artist - Title":
                        parts = base.split(" - ")
                        if len(parts) >= 2:
                            df.at[idx, 'Artist'] = parts[0].strip()
                            df.at[idx, 'Title'] = parts[1].strip()
                st.session_state.df_editor = df
                st.success("Titles Updated!")
                st.rerun()

        # --- GRID ---
        edited_df = st.data_editor(
            st.session_state.df_editor,
            hide_index=True,
            column_config={
                "Full Path": None,
                "Status": st.column_config.TextColumn(width="small", disabled=True),
                "Artist": st.column_config.TextColumn(width="medium", required=True),
                "Album": st.column_config.TextColumn(width="medium", required=True),
                "Title": st.column_config.TextColumn(width="medium", required=True),
                "File": st.column_config.TextColumn(width="large", disabled=True)
            },
            key="editor",
            use_container_width=True
        )
        
        if st.button("🧪 Test Run (Simulate Move)"):
            results = []
            progress = st.progress(0)
            rows = edited_df.to_dict('records')
            for i, row in enumerate(rows):
                results.append(process_file_dry_run(row))
                progress.progress((i+1)/len(rows))
            edited_df['Status'] = results
            st.session_state.df_editor = edited_df
            st.rerun()

else:
    st.info("No MP3s found here.")