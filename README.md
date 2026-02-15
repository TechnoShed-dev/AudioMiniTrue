Markdown

# AudioMiniTrue (v1.4.0)
The TechnoShed MP3 History Rewriter.

Designed to organize chaotic music folders into a pristine library structure without breaking existing Radio Station (AzuraCast) automation.

## 🚀 Key Features
- **Move vs. Symlink:** Choose to physically relocate files or create "ghost" links that point to original sources.
- **Housekeeping:** Automatically deletes empty source folders after a physical Move.
- **Nuclear Safety Lock:** Requires manual entry of 'LIVE MODE' to enable disk writes.
- **Bulk Tools:** Fill down Artist/Album tags and parse messy Radio Station filenames.
- **Smart Spacing:** Fixes mashed text/numbers (e.g., `SundaySession001` -> `Sunday Session 001`).

## 🛠️ Docker Setup
Map your root audio drive to `/music`. 

```yaml
services:
  minitrue:
    image: python:3.11-slim
    volumes:
      - /mnt/8tb/Audio:/music
      - .:/app
    ports:
      - "8303:8501"

📋 Usage

    Navigate to a folder.

    Select Symlink for Radio data or Move for DJ folders.

    Clean tags using the Cleaner and Parser tabs.

    Unlock LIVE MODE in the sidebar and commit.




### Next Step: 
Save these as `app.py` and `README.md`, then run:
```bash
git add .
git commit -m "v1.4.0: Housekeeping, Symlinks, and Nuclear Lock"
git push origin main