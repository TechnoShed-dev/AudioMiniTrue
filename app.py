# ------------------------------------------------------------------------------
# Project:      AudioMiniTrue
# Filename:     app.py
# Version:      v1.5.0
# Author:       Karl @ TechnoShed
# Date:         2026-02-15
# Description:  Added Track Number support for filenames like "01 - Title.mp3".
#               Automatically cleans track numbers from the Title tag.
# ------------------------------------------------------------------------------

import streamlit as st
import os
import pandas as pd
import re
import shutil
from mutagen.easyid3 import EasyID3
import mutagen

# --- Config & CSS ---
st.set_page_config(page_title="Minitrue v1.5", layout="wide", page_icon="🔢")
ROOT_DIR = "/music"
LIBRARY_DIR = os.path.join(ROOT_DIR, "Library")
PROTECTED_FOLDERS = ["jingles", "adverts", "station_ids", "sweepers", "news", "ftp_upload"]

# --- Helpers ---
def get_mp3_tags(file_path):
    try:
        audio = EasyID3(file_path)
        return {
            "Status": "Pending",
            "Track": audio.get('tracknumber', [''])[0].split('/')[0], # Handle 01/10 format
            "Artist": audio.get('artist', [''])[0],
            "Album": audio.get('album', [''])[0],
            "Title": audio.get('title', [''])[0],
            "File": os.path.basename(file_path),
            "Full Path": file_path
        }
    except Exception:
        return {"Status": "Error", "Track": "", "Artist": "", "Album": "", "Title": "", "File": os.path.basename(file_path), "Full Path": file_path}

def parse_track_from_filename(filename):
    """Detects leading numbers like '01 - ' or '01.' or '01_'"""
    match = re.match(r'^(\d+)', filename)
    if match:
        return match.group(1).zfill(2) # Ensure 01, 02 format
    return ""

def process_file_live(row, mode):
    src_path = row['Full Path']
    artist = re.sub(r'[\\/*?:"<>|]', "", str(row['Artist'])).strip()
    album = re.sub(r'[\\/*?:"<>|]', "", str(row['Album'])).strip()
    title = row['Title'].strip()
    track = row['Track'].strip()
    
    if not artist or not title: return "❌ Missing Data"
    
    target_album = album if album else "Singles"
    dest_dir = os.path.join(LIBRARY_DIR, artist, target_album)
    
    # Filename naming convention for Library
    filename_str = f"{track} - {title}.mp3" if track else f"{title}.mp3"
    dest_path = os.path.join(dest_dir, re.sub(r'[\\/*?:"<>|]', "", filename_str))

    try:
        audio = EasyID3(src_path)
        audio['artist'] = artist
        audio['album'] = target_album
        audio['title'] = title
        if track: audio['tracknumber'] = track
        audio.save()

        os.makedirs(dest_dir, exist_ok=True)
        if mode == "Move":
            shutil.move(src_path, dest_path)
            return "✅ Moved"
        else:
            os.symlink(os.path.relpath(src_path, dest_dir), dest_path)
            return "🔗 Linked"
    except Exception as e:
        return "❌ Error"

# --- UI Layout Updates ---
# [Note: UI logic below is condensed to highlight the new Track features]

if 'df_editor' in st.session_state and st.session_state.df_editor is not None:
    with st.expander("📝 Track & Title Tools"):
        if st.button("🔢 Extract Track Numbers from Filenames"):
            df = st.session_state.df_editor
            for idx, row in df.iterrows():
                track_val = parse_track_from_filename(row['File'])
                if track_val:
                    df.at[idx, 'Track'] = track_val
                    # Clean the Title: Remove the number and dashes from the start
                    clean_title = re.sub(r'^\d+[\s\.\-_]+', '', row['Title'])
                    df.at[idx, 'Title'] = clean_title
            st.session_state.df_editor = df
            st.rerun()

    # Reordered Grid to include Track
    st.data_editor(
        st.session_state.df_editor,
        column_order=["Status", "Track", "Artist", "Album", "Title", "File"],
        column_config={
            "Track": st.column_config.TextColumn(width="small"),
            "Artist": st.column_config.TextColumn(width="medium"),
            "Title": st.column_config.TextColumn(width="medium"),
            "File": st.column_config.TextColumn(disabled=True)
        },
        key="editor", use_container_width=True
    )