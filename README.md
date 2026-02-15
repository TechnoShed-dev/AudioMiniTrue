# AudioMiniTrue (v1.5.0)
The TechnoShed MP3 History Rewriter.

Organize DJ sets, Tape Packs, and Radio dumps into a pristine Library structure.

## 🚀 Version 1.5.0 Updates
- [cite_start]**Track Number Logic:** Automatically detects and extracts track numbers (e.g., `01. Song.mp3`) from filenames to populate ID3 tags.
- **Aggressive Housekeeping:** Recursively deletes empty source directories after a Move operation to keep your scratch folders clean.
- **Improved Sidebar:** Slimmer navigation with a persistent mode selector (Move vs. Symlink).

## 📋 Standard Workflow
1. **Load:** Navigate to a messy folder and hit `🔄 Load Files`.
2. [cite_start]**Bulk Fix:** Use `🛠️ Bulk & Track Tools` to extract track numbers or fill down Artist/Album tags[cite: 1, 2].
3. **Clean:** (Optional) Use the Cleaner tab to fix underscores or mashed text.
4. [cite_start]**Lock & Load:** Type `LIVE MODE` in the sidebar and choose your fate: **Move** (for DJ files) or **Symlink** (for AzuraCast data).

## 🏗️ Docker Environment
Ensure `/mnt/8tb/Audio` is mapped to `/music` in all music-related containers to maintain link resolution.

---
*Built for TechnoShed. v1.5.0 Beta Offering.*