# ------------------------------------------------------------------------------
# Project:      AudioMiniTrue
# Filename:     app.py
# Version:      v1.5.0
# Author:       Karl @ TechnoShed
# Date:         2026-02-15
# Description:  The MP3 History Rewriter.
#               - NEW: Track Number extraction (e.g. "01. Title" -> Track: 01).
#               - Housekeeping: Deletes empty source folders after Move.
#               - Mode: Move (Physical) or Symlink (Virtual Migration).
# ------------------------------------------------------------------------------

import streamlit as st
import os
import pandas as pd
import re
import shutil
from mutagen.easyid3 import EasyID3
import mutagen

# --- Config ---
st.set_page_config(page_title="Minitrue v1.5", layout="wide", page_icon="🔢")
ROOT_DIR = "/music"
LIBRARY_DIR = os.path.join(ROOT_DIR, "Library")
PROTECTED_FOLDERS = ["jingles", "adverts", "station_ids", "sweepers", "news", "ftp_upload"]

# --- CSS Injection ---
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

def parse_track_from_filename(filename):
    """Detects leading numbers like '01 - ' or '01.' or '01_'"""
    match = re.match(r'^(\d+)', filename)
    if match:
        return match.group(1).zfill(2)
    return ""

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
            "Track": audio.get('tracknumber', [''])[0].split('/')[0],
            "Artist": audio.get('artist', [''])[0],
            "Album": audio.get('album', [''])[0],
            "Title": audio.get('title', [''])[0],
            "File": os.path.basename(file_path),
            "Full Path": file_path
        }
    except Exception:
        return {"Status": "No Tags", "Track": "", "Artist": "", "Album": "", "Title": "", "File": os.path.basename(file_path), "Full Path": file_path}

# --- Core Logic ---
def process_file_live(row, mode):
    src_path = row['Full Path']
    src_dir = os.path.dirname(src_path)
    artist = sanitize_name(row['Artist'])
    album = sanitize_name(row['Album'])
    title = row['Title'].strip()
    track = row['Track'].strip()
    
    if not artist or not title: return "❌ Missing Data"
    
    target_album = album if album else "Singles"
    dest_dir = os.path.join(LIBRARY_DIR, artist, target_album)
    
    # Filename naming convention for Library
    filename_str = f"{track} - {title}.mp3" if track else f"{title}.mp3"
    dest_path = os.path.join(dest_dir, sanitize_name(filename_str))

    if os.path.exists(dest_path): return f"⚠️ Exists"

    try:
        audio = EasyID3(src_path)
        audio['artist'] = artist; audio['album'] = target_album; audio['title'] = title
        if track: audio['tracknumber'] = track
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
    except Exception:
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
        st.info("🔒 Simulation")
        unlock_code = st.text_input("Type 'LIVE MODE':", type="password")
        if unlock_code == "LIVE MODE": st.session_state.safety_lock = False; st.rerun()
    else:
        st.error("🔓 LIVE MODE")
        if st.button("🔒 Re-Lock"): st.session_state.safety_lock = True; st.rerun()

st.title(f"📻 Minitrue v1.5")
if not st.session_state.safety_lock:
    st.markdown(f'<div class="live-warning">☢️ LIVE MODE: {st.session_state.operation_mode.upper()} ☢️</div>', unsafe_allow_html=True)

dirs, files = get_files_in_directory(st.session_state.current_path)

# Breadcrumbs/Up
if st.session_state.current_path != ROOT_DIR:
    if st.button("⬅️ Up"): st.session_state.current_path = os.path.dirname(st.session_state.current_path); st.rerun()

if dirs:
    st.write("### Subfolders")
    cols = st.columns(5)
    for i, d in enumerate(dirs):
        if cols[i % 5].button(f"📁 {d}", key=f"dir_{d}"):
            st.session_state.current_path = os.path.join(st.session_state.current_path, d); st.rerun()

st.divider()
if files:
    if st.button("🔄 Load Files"):
        tag_data = [get_mp3_tags(os.path.join(st.session_state.current_path, f)) for f in files]
        st.session_state.df_editor = pd.DataFrame(tag_data); st.rerun()

    if st.session_state.df_editor is not None:
        with st.expander("🛠️ Bulk & Track Tools"):
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("⬇️ Fill Down (Artist/Album)"):
                    st.session_state.df_editor[['Artist', 'Album']] = st.session_state.df_editor[['Artist', 'Album']].replace('', pd.NA).ffill().fillna('')
                    st.rerun()
            with c2:
                if st.button("🔢 Extract Tracks from Files"):
                    df = st.session_state.df_editor
                    for idx, row in df.iterrows():
                        t = parse_track_from_filename(row['File'])
                        if t:
                            df.at[idx, 'Track'] = t
                            df.at[idx, 'Title'] = re.sub(r'^\d+[\s\.\-_]+', '', row['Title'])
                    st.session_state.df_editor = df; st.rerun()
            with c3:
                if st.button("✨ Guess Folder Tags"):
                    curr, parent = os.path.basename(st.session_state.current_path), os.path.basename(os.path.dirname(st.session_state.current_path))
                    st.session_state.df_editor['Artist'] = st.session_state.df_editor['Artist'].apply(lambda x: parent if x == '' else x)
                    st.session_state.df_editor['Album'] = st.session_state.df_editor['Album'].apply(lambda x: curr if x == '' else x); st.rerun()

        edited_df = st.data_editor(st.session_state.df_editor, hide_index=True, column_order=["Status", "Track", "Artist", "Album", "Title", "File"], key="editor", use_container_width=True)
        
        if st.session_state.safety_lock:
            if st.button(f"🧪 Simulate {st.session_state.operation_mode}"):
                st.info("Simulation mode triggered. Check status column.")
        else:
            if st.button(f"☢️ COMMIT {st.session_state.operation_mode.upper()} ☢️", type="primary"):
                res = [process_file_live(r, st.session_state.operation_mode) for r in edited_df.to_dict('records')]
                edited_df['Status'] = res; st.session_state.df_editor = edited_df; st.rerun()