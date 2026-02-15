# ------------------------------------------------------------------------------
# Project:      AudioMiniTrue
# Filename:     app.py
# Version:      v1.4.0
# Author:       Karl @ TechnoShed
# Date:         2026-02-15
# Website:      https://technoshed.co.uk
# Description:  The MP3 History Rewriter.
#               - NEW: Automatic cleanup of empty source folders after Move.
#               - Mode: Move (Physical) or Symlink (Virtual Migration).
#               - Bulk Tagging & Smart Spacing for Radio Station dumps.
# ------------------------------------------------------------------------------

import streamlit as st
import os
import pandas as pd
import re
import shutil
from mutagen.easyid3 import EasyID3
import mutagen

# --- Config ---
st.set_page_config(page_title="Minitrue v1.4", layout="wide", page_icon="🧹")
ROOT_DIR = "/music"
LIBRARY_DIR = os.path.join(ROOT_DIR, "Library")
PROTECTED_FOLDERS = ["jingles", "adverts", "station_ids", "sweepers", "news", "ftp_upload"]

# --- CSS Injection (Slim Sidebar & Layout) ---
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] { min-width: 180px; max-width: 220px; }
        .block-container { padding-top: 1rem; padding-left: 2rem; padding-right: 2rem; }
        .live-warning { color: #ff4b4b; font-weight: bold; border: 1px solid #ff4b4b; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Session State ---
if 'current_path' not in st.session_state: st.session_state.current_path = ROOT_DIR
if 'df_editor' not in st.session_state: st.session_state.df_editor = None
if 'safety_lock' not in st.session_state: st.session_state.safety_lock = True
if 'operation_mode' not in st.session_state: st.session_state.operation_mode = "Move"

# --- Helper Functions ---
def sanitize_name(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

def remove_empty_folders(path):
    """Recursively removes empty folders up to ROOT_DIR."""
    if not os.path.isdir(path) or path == ROOT_DIR:
        return
    if os.path.basename(path).lower() in PROTECTED_FOLDERS:
        return
    if not os.listdir(path):
        try:
            os.rmdir(path)
            remove_empty_folders(os.path.dirname(path))
        except Exception:
            pass

def get_files_in_directory(path):
    try:
        items = os.listdir(path)
        dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
        files = [f for f in items if f.lower().endswith('.mp3')]
        dirs.sort(); files.sort()
        return dirs, files
    except Exception as e:
        st.error(f"Error accessing path: {e}")
        return [], []

def get_mp3_tags(file_path):
    try:
        audio = EasyID3(file_path)
        return {
            "Status": "Pending",
            "Artist": audio.get('artist', [''])[0],
            "Album": audio.get('album', [''])[0],
            "Title": audio.get('title', [''])[0],
            "File": os.path.basename(file_path),
            "Full Path": file_path
        }
    except mutagen.id3.ID3NoHeaderError:
        return {"Status": "No Tags", "Artist": "", "Album": "", "Title": "", "File": os.path.basename(file_path), "Full Path": file_path}
    except Exception:
        return {"Status": "Error", "Artist": "", "Album": "", "Title": "", "File": os.path.basename(file_path), "Full Path": file_path}

def clean_radio_filename(filename, operation):
    base = os.path.splitext(filename)[0]
    if operation == "Strip Numeric Prefix": base = re.sub(r'^\d+_+', '', base)
    elif operation == "Underscores to Spaces": base = base.replace("_", " ")
    elif operation == "Title Case": base = base.title()
    elif operation == "Smart Space (Session001 -> Session 001)":
        base = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', base)
        base = base[0].upper() + base[1:] if base else base
    return base

# --- Core Logic ---
def process_file_dry_run(row, mode):
    src_path = row['Full Path']
    artist = sanitize_name(row['Artist'])
    album = sanitize_name(row['Album'])
    title = sanitize_name(row['Title'])
    if not artist or not title: return "❌ Missing Tags"
    for p in PROTECTED_FOLDERS:
        if f"/{p}/" in src_path or src_path.endswith(f"/{p}"): return f"🛡️ Protected"
    target_album = album if album else "Singles"
    return f"✅ (Sim) {mode.upper()} -> /Library/{artist}/{target_album}/..."

def process_file_live(row, mode):
    src_path = row['Full Path']
    src_dir = os.path.dirname(src_path)
    artist = sanitize_name(row['Artist'])
    album_tag = sanitize_name(row['Album'])
    title_tag = row['Title'].strip()
    
    if not artist or not title_tag: return "❌ Missing Data"
    for p in PROTECTED_FOLDERS:
        if f"/{p}/" in src_path or src_path.endswith(f"/{p}"): return f"🛡️ Protected"
    
    target_album = album_tag if album_tag else "Singles"
    dest_dir = os.path.join(LIBRARY_DIR, artist, target_album)
    dest_path = os.path.join(dest_dir, sanitize_name(title_tag) + ".mp3")

    if os.path.exists(dest_path): return f"⚠️ Exists"

    try:
        try:
            audio = EasyID3(src_path)
        except mutagen.id3.ID3NoHeaderError:
            audio = EasyID3(); audio.save(src_path); audio = EasyID3(src_path)
        
        audio['artist'] = artist; audio['album'] = target_album; audio['title'] = title_tag
        audio.save()

        os.makedirs(dest_dir, exist_ok=True)
        if mode == "Move":
            shutil.move(src_path, dest_path)
            remove_empty_folders(src_dir)
            return "✅ Moved"
        else:
            rel_source = os.path.relpath(src_path, dest_dir)
            os.symlink(rel_source, dest_path)
            return "🔗 Linked"
    except Exception as e:
        return f"❌ Error"

# --- UI ---
with st.sidebar:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
    st.markdown("### Nav")
    if st.button("🏠 Root"): st.session_state.current_path = ROOT_DIR; st.rerun()
    st.divider()
    st.markdown("### ⚙️ Mode")
    st.session_state.operation_mode = st.radio("Action Type:", ["Move", "Symlink"])
    st.divider()
    st.markdown("### ☢️ Lock")
    if st.session_state.safety_lock:
        st.info(f"🔒 Simulation ({st.session_state.operation_mode})")
        unlock_code = st.text_input("Type 'LIVE MODE':", type="password")
        if unlock_code == "LIVE MODE": st.session_state.safety_lock = False; st.rerun()
    else:
        st.error(f"🔓 LIVE {st.session_state.operation_mode.upper()}")
        if st.button("🔒 Re-Lock"): st.session_state.safety_lock = True; st.rerun()

st.title(f"📻 Minitrue v1.4")
if not st.session_state.safety_lock:
    st.markdown(f'<div class="live-warning">☢️ LIVE MODE: FILES WILL BE {st.session_state.operation_mode.upper()}D ☢️</div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 6])
with col1:
    if st.session_state.current_path != ROOT_DIR:
        if st.button("⬅️ Up"): st.session_state.current_path = os.path.dirname(st.session_state.current_path); st.rerun()

dirs, files = get_files_in_directory(st.session_state.current_path)

if dirs:
    st.write("### Subfolders")
    cols = st.columns(5)
    for i, d in enumerate(dirs):
        label = f"📁 {d}"
        if d.lower() in PROTECTED_FOLDERS: label = f"🛡️ {d}"
        if cols[i % 5].button(label, key=f"dir_{d}_{i}"): st.session_state.current_path = os.path.join(st.session_state.current_path, d); st.rerun()

st.divider()
if files:
    if st.button("🔄 Load Files"):
        tag_data = []
        for f in files:
            tag_data.append(get_mp3_tags(os.path.join(st.session_state.current_path, f)))
        st.session_state.df_editor = pd.DataFrame(tag_data)

    if st.session_state.df_editor is not None:
        with st.expander("🛠️ Bulk Tools"):
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("⬇️ Artist Fill Down"):
                    st.session_state.df_editor['Artist'] = st.session_state.df_editor['Artist'].replace('', pd.NA).ffill().fillna(''); st.rerun()
            with b2:
                if st.button("⬇️ Album Fill Down"):
                    st.session_state.df_editor['Album'] = st.session_state.df_editor['Album'].replace('', pd.NA).ffill().fillna(''); st.rerun()
            with b3:
                if st.button("✨ Guess Folder Tags"):
                    curr = os.path.basename(st.session_state.current_path)
                    parent = os.path.basename(os.path.dirname(st.session_state.current_path))
                    st.session_state.df_editor['Artist'] = st.session_state.df_editor['Artist'].apply(lambda x: parent if x == '' else x)
                    st.session_state.df_editor['Album'] = st.session_state.df_editor['Album'].apply(lambda x: curr if x == '' else x); st.rerun()

        tab_clean, tab_parse = st.tabs(["🧹 Cleaner", "📝 Parser"])
        with tab_clean:
            op = st.selectbox("Operation", ["Smart Space (Session001 -> Session 001)", "Strip Numeric Prefix", "Underscores to Spaces", "Title Case"])
            if st.button("Apply"):
                st.session_state.df_editor['File'] = st.session_state.df_editor['File'].apply(lambda x: clean_radio_filename(x, op) + ".mp3"); st.rerun()
        with tab_parse:
            pmode = st.radio("Pattern", ["Title Only", "Artist - Title", "Artist - Album - Title"], horizontal=True)
            if st.button("Apply Tags"):
                df = st.session_state.df_editor
                for idx, row in df.iterrows():
                    base = os.path.splitext(row['File'])[0]
                    parts = base.split(" - ")
                    if pmode == "Title Only": df.at[idx, 'Title'] = base.strip()
                    elif pmode == "Artist - Title" and len(parts) >= 2:
                        df.at[idx, 'Artist'] = parts[0].strip(); df.at[idx, 'Title'] = parts[1].strip()
                    elif pmode == "Artist - Album - Title" and len(parts) >= 3:
                        df.at[idx, 'Artist'] = parts[0].strip(); df.at[idx, 'Album'] = parts[1].strip(); df.at[idx, 'Title'] = parts[2].strip()
                st.session_state.df_editor = df; st.rerun()

        edited_df = st.data_editor(st.session_state.df_editor, hide_index=True, column_order=["Status", "Artist", "Album", "Title", "File"], key="editor", use_container_width=True)
        
        if st.session_state.safety_lock:
            if st.button(f"🧪 Simulate {st.session_state.operation_mode}"):
                res = [process_file_dry_run(r, st.session_state.operation_mode) for r in edited_df.to_dict('records')]
                edited_df['Status'] = res; st.session_state.df_editor = edited_df; st.rerun()
        else:
            if st.button(f"☢️ COMMIT {st.session_state.operation_mode.upper()} ☢️", type="primary"):
                res = [process_file_live(r, st.session_state.operation_mode) for r in edited_df.to_dict('records')]
                edited_df['Status'] = res; st.session_state.df_editor = edited_df; st.rerun()
else: st.info("No MP3s found.")