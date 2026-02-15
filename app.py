# ------------------------------------------------------------------------------
# Project:      AudioMiniTrue
# Filename:     app.py
# Version:      v1.7.1
# Author:       Karl @ TechnoShed
# Date:         2026-02-15
# Description:  - NEW: Support for .m4a files (ALAC/AAC).
#               - Supports .mp3, .flac, .wav, .m4a, and .cue sidecars.
#               - Auto-loads files on folder entry & recursive housekeeping.
# ------------------------------------------------------------------------------

import streamlit as st
import os
import pandas as pd
import re
import shutil
import logging
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
import mutagen

# --- Logging Setup ---
logging.basicConfig(
    filename='minitrue.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Config ---
st.set_page_config(page_title="Minitrue v1.7.1", layout="wide", page_icon="🎼")
ROOT_DIR = "/music"
LIBRARY_DIR = os.path.join(ROOT_DIR, "Library")
PROTECTED_FOLDERS = ["jingles", "adverts", "station_ids", "sweepers", "news", "ftp_upload"]

# --- Session State ---
if 'current_path' not in st.session_state: st.session_state.current_path = ROOT_DIR
if 'last_scanned_path' not in st.session_state: st.session_state.last_scanned_path = None
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

def get_audio_tags(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.cue':
        return {"Status": "Sidecar", "Track": "", "Artist": "", "Album": "", "Title": os.path.basename(file_path), "File": os.path.basename(file_path), "Full Path": file_path}
    
    try:
        if ext == '.flac':
            audio = FLAC(file_path)
            res = {"Track": audio.get('tracknumber', [''])[0], "Artist": audio.get('artist', [''])[0], "Album": audio.get('album', [''])[0], "Title": audio.get('title', [''])[0]}
        elif ext == '.m4a':
            audio = MP4(file_path)
            res = {
                "Track": str(audio.get('trkn', [(0,0)])[0][0]) if audio.get('trkn') else "",
                "Artist": audio.get('\xa9ART', [''])[0],
                "Album": audio.get('\xa9alb', [''])[0],
                "Title": audio.get('\xa9nam', [''])[0]
            }
        elif ext == '.wav':
            try: 
                audio = WAVE(file_path)
                res = {"Track": audio.get('tracknumber', [''])[0], "Artist": audio.get('artist', [''])[0], "Album": audio.get('album', [''])[0], "Title": audio.get('title', [''])[0]}
            except: 
                return {"Status": "WAV (No Tags)", "Track": "", "Artist": "", "Album": "", "Title": os.path.basename(file_path), "File": os.path.basename(file_path), "Full Path": file_path}
        else:
            audio = EasyID3(file_path)
            res = {"Track": audio.get('tracknumber', [''])[0], "Artist": audio.get('artist', [''])[0], "Album": audio.get('album', [''])[0], "Title": audio.get('title', [''])[0]}
            
        return {
            "Status": "Pending",
            "Track": res["Track"].split('/')[0],
            "Artist": res["Artist"],
            "Album": res["Album"],
            "Title": res["Title"],
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

def load_files_into_state():
    try:
        items = os.listdir(st.session_state.current_path)
        files = [f for f in items if f.lower().endswith(('.mp3', '.flac', '.wav', '.cue', '.m4a'))]
        if files:
            data = [get_audio_tags(os.path.join(st.session_state.current_path, f)) for f in files]
            st.session_state.df_editor = pd.DataFrame(data)
        else:
            st.session_state.df_editor = None
        st.session_state.last_scanned_path = st.session_state.current_path
    except Exception as e:
        st.error(f"Access error: {e}")

def process_file_live(row, mode):
    src_path = row['Full Path']
    src_dir = os.path.dirname(src_path)
    ext = os.path.splitext(src_path)[1].lower()
    if ext == '.cue': return "📄 Sidecar (Auto)"

    artist, album, title, track = sanitize_name(row['Artist']), sanitize_name(row['Album']), row['Title'].strip(), row['Track'].strip()
    if not artist or not title: return "❌ Missing Data"
    
    target_album = album if album else "Singles"
    dest_dir = os.path.join(LIBRARY_DIR, artist, target_album)
    filename_str = f"{track} - {title}{ext}" if track else f"{title}{ext}"
    dest_path = os.path.join(dest_dir, sanitize_name(filename_str))
    
    if os.path.exists(dest_path): return f"⚠️ Exists"

    try:
        if ext == '.flac':
            audio = FLAC(src_path)
            audio['artist'], audio['album'], audio['title'] = artist, target_album, title
            if track: audio['tracknumber'] = track
            audio.save()
        elif ext == '.m4a':
            audio = MP4(src_path)
            audio['\xa9ART'] = artist; audio['\xa9alb'] = target_album; audio['\xa9nam'] = title
            if track:
                try: audio['trkn'] = [(int(track), 0)]
                except: pass
            audio.save()
        elif ext == '.wav':
            audio = WAVE(src_path)
            if not audio.tags: audio.add_tags()
            audio.tags.add(mutagen.id3.TPE1(encoding=3, text=artist))
            audio.tags.add(mutagen.id3.TALB(encoding=3, text=target_album))
            audio.tags.add(mutagen.id3.TIT2(encoding=3, text=title))
            if track: audio.tags.add(mutagen.id3.TRCK(encoding=3, text=track))
            audio.save()
        else:
            try: audio = EasyID3(src_path)
            except: audio = EasyID3(); audio.save(src_path); audio = EasyID3(src_path)
            audio['artist'], audio['album'], audio['title'] = artist, target_album, title
            if track: audio['tracknumber'] = track
            audio.save()

        os.makedirs(dest_dir, exist_ok=True)
        if mode == "Move":
            shutil.move(src_path, dest_path)
            logging.info(f"MOVE: {src_path} -> {dest_path}")
        else:
            os.symlink(os.path.relpath(src_path, dest_dir), dest_path)
            logging.info(f"LINK: {dest_path} -> {src_path}")

        # Sidecar CUE handling
        cue_src = os.path.splitext(src_path)[0] + ".cue"
        if os.path.exists(cue_src):
            cue_dest = os.path.join(dest_dir, sanitize_name(f"{track} - {title}.cue" if track else f"{title}.cue"))
            if mode == "Move":
                shutil.move(cue_src, cue_dest)
            else:
                os.symlink(os.path.relpath(cue_src, dest_dir), cue_dest)

        if mode == "Move": remove_empty_folders(src_dir)
        return "✅ Done"
    except Exception as e:
        logging.error(f"FAILURE: {src_path} - {e}")
        return f"❌ Error"

# --- UI ---
st.title("📻 Minitrue v1.7.1")

with st.sidebar:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
    if st.button("🏠 Root Menu"): st.session_state.current_path = ROOT_DIR; st.rerun()
    if st.button("🔄 Force Refresh"): load_files_into_state(); st.rerun()
    st.divider()
    st.session_state.operation_mode = st.radio("Action:", ["Move", "Symlink"])
    st.divider()
    if st.session_state.safety_lock:
        unlock = st.text_input("Type 'LIVE MODE':", type="password")
        if unlock == "LIVE MODE": st.session_state.safety_lock = False; st.rerun()
    else:
        st.error("🔓 LIVE MODE")
        if st.button("🔒 Re-Lock"): st.session_state.safety_lock = True; st.rerun()

# Breadcrumbs
path_parts = [p for p in st.session_state.current_path.split("/") if p]
b_cols = st.columns(len(path_parts) + 1)
with b_cols[0]:
    if st.button("📁 Root"): st.session_state.current_path = ROOT_DIR; st.rerun()
full_p = "/"
for i, part in enumerate(path_parts):
    full_p += part + "/"
    with b_cols[i+1]:
        if st.button(f"{part} ➔", key=f"b_{i}"): st.session_state.current_path = full_p; st.rerun()

st.divider()

try:
    items = sorted(os.listdir(st.session_state.current_path))
    dirs = [d for d in items if os.path.isdir(os.path.join(st.session_state.current_path, d))]
except: dirs = []

if st.session_state.current_path != ROOT_DIR:
    if st.button("⬅️ Up One"): st.session_state.current_path = os.path.dirname(st.session_state.current_path); st.rerun()

if dirs:
    st.write("### Subfolders")
    cols = st.columns(5)
    for i, d in enumerate(dirs):
        if cols[i % 5].button(f"📁 {d}", key=f"dir_{d}"):
            st.session_state.current_path = os.path.join(st.session_state.current_path, d); st.rerun()

st.divider()

if st.session_state.current_path != st.session_state.last_scanned_path:
    load_files_into_state()

if st.session_state.df_editor is not None and not st.session_state.df_editor.empty:
    st.subheader(f"🎵 Files in `{os.path.basename(st.session_state.current_path.rstrip('/'))}`")
    with st.expander("🛠️ Advanced Tools", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⬇️ Fill Down (Art/Alb)"):
                st.session_state.df_editor[['Artist', 'Album']] = st.session_state.df_editor[['Artist', 'Album']].replace('', pd.NA).ffill().fillna(''); st.rerun()
        with c2:
            if st.button("🔥 Super-Parse"):
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
                curr = os.path.basename(st.session_state.current_path.rstrip('/'))
                par = os.path.basename(os.path.dirname(st.session_state.current_path.rstrip('/')))
                st.session_state.df_editor['Artist'] = st.session_state.df_editor['Artist'].apply(lambda x: par if x == '' else x)
                st.session_state.df_editor['Album'] = st.session_state.df_editor['Album'].apply(lambda x: curr if x == '' else x); st.rerun()

    edited_df = st.data_editor(st.session_state.df_editor, hide_index=True, column_order=["Status", "Track", "Artist", "Album", "Title", "File"], key="editor", use_container_width=True)
    
    if not st.session_state.safety_lock:
        if st.button(f"☢️ COMMIT {st.session_state.operation_mode.upper()} ☢️", type="primary"):
            res = [process_file_live(r, st.session_state.operation_mode) for r in edited_df.to_dict('records')]
            edited_df['Status'] = res; st.session_state.df_editor = edited_df; st.rerun()
    else:
        st.info("Simulation mode active. Unlock in sidebar to commit changes.")
else:
    st.info("No audio files detected.")