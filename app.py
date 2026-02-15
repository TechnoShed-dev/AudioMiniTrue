# ------------------------------------------------------------------------------
# Project:      AudioMiniTrue
# Filename:     app.py
# Version:      v1.6.2
# Author:       Karl @ TechnoShed
# Date:         2026-02-15
# Website:      https://technoshed.co.uk
# Description:  The MP3/FLAC History Rewriter.
#               - NEW: Breadcrumb navigation for deep folder awareness.
#               - NEW: Advanced Super-Parser for complex rave/DJ filenames.
#               - FLAC & MP3 support with Audit Logging.
#               - Recursive Housekeeping of empty folders.
# ------------------------------------------------------------------------------

import streamlit as st
import os
import pandas as pd
import re
import shutil
import logging
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
import mutagen

# --- Logging Setup ---
logging.basicConfig(
    filename='minitrue.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Config ---
st.set_page_config(page_title="Minitrue v1.6.2", layout="wide", page_icon="🎼")
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
        .breadcrumb-item { color: #007bff; text-decoration: none; font-weight: bold; }
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
    if not os.path.isdir(path) or path == ROOT_DIR:
        return
    if os.path.basename(path).lower() in PROTECTED_FOLDERS:
        return
    if not os.listdir(path):
        try:
            os.rmdir(path)
            logging.info(f"HOUSEKEEPING: Removed empty folder {path}")
            remove_empty_folders(os.path.dirname(path))
        except Exception:
            pass

def get_files_in_directory(path):
    try:
        items = os.listdir(path)
        dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
        files = [f for f in items if f.lower().endswith(('.mp3', '.flac'))]
        dirs.sort(); files.sort()
        return dirs, files
    except Exception as e:
        st.error(f"Error accessing path: {e}")
        return [], []

def get_audio_tags(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.flac':
            audio = FLAC(file_path)
            return {
                "Status": "Pending",
                "Track": audio.get('tracknumber', [''])[0].split('/')[0],
                "Artist": audio.get('artist', [''])[0],
                "Album": audio.get('album', [''])[0],
                "Title": audio.get('title', [''])[0],
                "File": os.path.basename(file_path),
                "Full Path": file_path
            }
        else:
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

def advanced_parse(filename):
    base = os.path.splitext(filename)[0]
    track = ""
    track_match = re.match(r'^(\d+)[\s\.\-_]*', base)
    if track_match:
        track = track_match.group(1).zfill(2)
        base = re.sub(r'^\d+[\s\.\-_]*', '', base)
    
    temp_base = base.replace('@', '-').replace('_', ' ')
    parts = [p.strip() for p in re.split(r'\s-\s|\s-\s|-\s|\s-', temp_base) if p.strip()]
    
    res = {"Track": track, "Artist": "", "Album": "", "Title": base}
    if len(parts) == 2:
        res["Artist"] = parts[0]; res["Title"] = parts[1]
    elif len(parts) >= 3:
        res["Artist"] = parts[0]; res["Album"] = parts[1]; res["Title"] = " - ".join(parts[2:])
    return res

def process_file_live(row, mode):
    src_path = row['Full Path']
    src_dir = os.path.dirname(src_path)
    ext = os.path.splitext(src_path)[1].lower()
    artist = sanitize_name(row['Artist'])
    album = sanitize_name(row['Album'])
    title = row['Title'].strip()
    track = row['Track'].strip()
    
    if not artist or not title: 
        logging.warning(f"SKIP: Missing metadata for {src_path}")
        return "❌ Missing Data"
    
    target_album = album if album else "Singles"
    dest_dir = os.path.join(LIBRARY_DIR, artist, target_album)
    filename_str = f"{track} - {title}{ext}" if track else f"{title}{ext}"
    dest_path = os.path.join(dest_dir, sanitize_name(filename_str))

    if os.path.exists(dest_path): 
        logging.warning(f"COLLISION: {dest_path} already exists.")
        return f"⚠️ Exists"

    try:
        if ext == '.flac':
            audio = FLAC(src_path)
            audio['artist'] = artist; audio['album'] = target_album; audio['title'] = title
            if track: audio['tracknumber'] = track
        else:
            try:
                audio = EasyID3(src_path)
            except mutagen.id3.ID3NoHeaderError:
                audio = EasyID3(); audio.save(src_path); audio = EasyID3(src_path)
            audio['artist'] = artist; audio['album'] = target_album; audio['title'] = title
            if track: audio['tracknumber'] = track
        audio.save()

        os.makedirs(dest_dir, exist_ok=True)
        if mode == "Move":
            shutil.move(src_path, dest_path)
            logging.info(f"MOVE: {src_path} -> {dest_path}")
            remove_empty_folders(src_dir)
            return "✅ Moved"
        else:
            rel_source = os.path.relpath(src_path, dest_dir)
            os.symlink(rel_source, dest_path)
            logging.info(f"LINK: {dest_path} -> {src_path}")
            return "🔗 Linked"
    except Exception as e:
        logging.error(f"FAILURE: {src_path} - {e}")
        return f"❌ Error"

# --- UI ---
with st.sidebar:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
    st.markdown("### Nav")
    if st.button("🏠 Root"): st.session_state.current_path = ROOT_DIR; st.rerun()
    st.divider()
    st.markdown("### ⚙️ Mode")
    st.session_state.operation_mode = st.radio("Action:", ["Move", "Symlink"])
    st.divider()
    st.markdown("### ☢️ Lock")
    if st.session_state.safety_lock:
        unlock = st.text_input("Type 'LIVE MODE':", type="password")
        if unlock == "LIVE MODE": st.session_state.safety_lock = False; st.rerun()
    else:
        if st.button("🔒 Re-Lock"): st.session_state.safety_lock = True; st.rerun()

st.title(f"📻 Minitrue v1.6.2")

# Breadcrumbs
path_parts = st.session_state.current_path.strip("/").split("/")
full_bread_path = "/"
b_cols = st.columns(len(path_parts) + 1)
with b_cols[0]:
    if st.button("📁 Root", key="bread_root"): st.session_state.current_path = ROOT_DIR; st.rerun()
for i, part in enumerate(path_parts):
    if not part: continue
    with b_cols[i+1]:
        if st.button(f"{part} ➔", key=f"bread_{i}"):
            st.session_state.current_path = "/" + "/".join(path_parts[:i+1]); st.rerun()

st.divider()
if not st.session_state.safety_lock:
    st.markdown(f'<div class="live-warning">☢️ LIVE MODE: {st.session_state.operation_mode.upper()} ☢️</div>', unsafe_allow_html=True)

col_up, col_info = st.columns([1, 5])
with col_up:
    if st.session_state.current_path != ROOT_DIR:
        if st.button("⬅️ Up One"): st.session_state.current_path = os.path.dirname(st.session_state.current_path); st.rerun()
with col_info:
    st.markdown(f"**Path:** `{st.session_state.current_path}`")

dirs, files = get_files_in_directory(st.session_state.current_path)

if dirs:
    st.write("### Subfolders")
    cols = st.columns(5)
    for i, d in enumerate(dirs):
        if cols[i % 5].button(f"📁 {d}", key=f"dir_{d}"):
            st.session_state.current_path = os.path.join(st.session_state.current_path, d); st.rerun()

st.divider()
if files:
    if st.button("🔄 Load Files"):
        st.session_state.df_editor = pd.DataFrame([get_audio_tags(os.path.join(st.session_state.current_path, f)) for f in files]); st.rerun()

    if st.session_state.df_editor is not None:
        with st.expander("🛠️ Advanced Tools", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("⬇️ Fill Down (Artist/Album)"):
                    st.session_state.df_editor[['Artist', 'Album']] = st.session_state.df_editor[['Artist', 'Album']].replace('', pd.NA).ffill().fillna(''); st.rerun()
            with c2:
                if st.button("🔥 Super-Parse Filenames"):
                    df = st.session_state.df_editor
                    for idx, row in df.iterrows():
                        p = advanced_parse(row['File'])
                        if p["Track"]: df.at[idx, 'Track'] = p["Track"]
                        if p["Artist"]: df.at[idx, 'Artist'] = p["Artist"]
                        if p["Album"]: df.at[idx, 'Album'] = p["Album"]
                        df.at[idx, 'Title'] = p["Title"]
                    st.session_state.df_editor = df; st.rerun()
            with c3:
                if st.button("✨ Guess Folder Tags"):
                    curr, parent = os.path.basename(st.session_state.current_path), os.path.basename(os.path.dirname(st.session_state.current_path))
                    st.session_state.df_editor['Artist'] = st.session_state.df_editor['Artist'].apply(lambda x: parent if x == '' else x)
                    st.session_state.df_editor['Album'] = st.session_state.df_editor['Album'].apply(lambda x: curr if x == '' else x); st.rerun()

        edited_df = st.data_editor(st.session_state.df_editor, hide_index=True, column_order=["Status", "Track", "Artist", "Album", "Title", "File"], key="editor", use_container_width=True)
        
        if not st.session_state.safety_lock:
            if st.button(f"☢️ COMMIT {st.session_state.operation_mode.upper()} ☢️", type="primary"):
                res = [process_file_live(r, st.session_state.operation_mode) for r in edited_df.to_dict('records')]
                edited_df['Status'] = res; st.session_state.df_editor = edited_df; st.rerun()
        else:
            if st.button(f"🧪 Simulate {st.session_state.operation_mode}"):
                st.info("Simulation mode active.")
else: st.info("No audio files found.")