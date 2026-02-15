Markdown

# Minitrue: Audio History Rewriter

![TechnoShed](https://technoshed.co.uk/logo.jpg)

> *"Who controls the past controls the future. Who controls the present controls the past."*

**Minitrue** is a specialized, web-based tool for "rewriting history"—specifically, the metadata history of your MP3 library. Built for **TechnoShed** to run on a Raspberry Pi via Docker, it is designed to handle the messy reality of DJ sets, Tape Packs, and Radio Station automation dumps that standard taggers (like MusicBrainz Picard) often choke on.

---

## 📋 Project Info
* **Version:** v0.11.0 (Beta)
* **Status:** Active Development (Simulation Mode Enabled)
* **Author:** Karl @ TechnoShed
* **Website:** [www.technoshed.co.uk](https://technoshed.co.uk)
* **Repo:** [github.com/TechnoShed-dev/ble-scanner](https://github.com/TechnoShed-dev/ble-scanner) *(Note: Repo name legacy, project is Minitrue)*

---

## 🚀 Key Features

### 1. 📼 Tape Pack & DJ Set Support
Standard databases don't know about a "Helter Skelter 1993" tape pack. Minitrue does.
* **Regex Pattern Matching:** Instantly parse filenames like `Helter Skelter - 17-09-1993 - Grooverider.mp3` into correct Artist, Album, and Title tags.
* **Smart Cleaning:** Automatically formats "Scene Release" names (removing underscores and `01-` prefixes).

### 2. 📻 Radio Station Decontamination
Clean up messy exports from AzuraCast or Centova Cast.
* **Prefix Stripper:** Removes automation IDs (e.g., `1001_artist_name.mp3` → `Artist Name`).
* **Smart Spacer:** Splits mashed text/numbers (e.g., `SundaySession001` → `Sunday Session 001`).
* **Protected Folders:** automatically locks system folders (`jingles`, `adverts`, `sweepers`) to prevent accidental tagging.

### 3. 🛠️ Power User Tools
* **Bulk Edit:** "Fill Down" artists (Excel style) or "Set All" for quick folder organization.
* **Simulation Mode:** currently defaults to a "Dry Run" that shows you exactly where files *would* be moved without touching your disk.
* **Slim UI:** Optimized for efficient workflows on smaller screens.

---

## 🛠️ Installation (Docker)

Minitrue is designed to run in a container.

### 1. Clone the Repo
```bash
git clone [https://github.com/TechnoShed-dev/ble-scanner.git](https://github.com/TechnoShed-dev/ble-scanner.git) minitrue
cd minitrue

2. Configure Docker Compose

Open docker-compose.yml and update the volume path to point to your actual music library.
YAML

version: '3.8'
services:
  minitrue:
    build: .
    container_name: minitrue
    ports:
      - "8303:8501"
    volumes:
      - .:/app
      - /mnt/8tb/Audio:/music  # <--- UPDATE THIS PATH
    restart: unless-stopped

3. Run
Bash

docker-compose up -d --build

Access the interface at: http://<your-pi-ip>:8303
📂 File Structure

The project follows TechnoShed standards:
Plaintext

minitrue/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies (streamlit, mutagen, pandas)
├── Dockerfile          # Container definition
├── docker-compose.yml  # Service orchestration
└── README.md           # This file

⚠️ Beta Warning

Simulation Mode is currently ACTIVE.
The process_file function is set to "Dry Run" by default. It will return a status message (e.g., "✅ Would move to...") but will not modify files.
To enable live writing, edit app.py and swap the process_file_dry_run function for the live version (coming in v1.0).

© 2026 TechnoShed. All rights reserved.