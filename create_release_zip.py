import os
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_ZIP = os.path.join(BASE_DIR, "AetherCraft-Server-Complete.zip")
RELEASES_DIR = os.path.join(BASE_DIR, "releases")
os.makedirs(RELEASES_DIR, exist_ok=True)
OUT_ZIP_RELEASE = os.path.join(RELEASES_DIR, "AetherCraft-v1.0.0-Full.zip")

EXCLUDE_DIRS = {
    ".aether", "target", ".git", "__pycache__", "cache", "logs", 
    "runtime", "world", "world_nether", "world_the_end"
}
EXCLUDE_EXTS = {".log", ".tmp"}

print("[*] Creation de l'archive ZIP complete AetherCraft...")
files_added = 0

with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith(".WebView2")]
        
        for file in files:
            if file == os.path.basename(OUT_ZIP) or file == os.path.basename(OUT_ZIP_RELEASE):
                continue
            _, ext = os.path.splitext(file)
            if ext in EXCLUDE_EXTS:
                continue
            
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, BASE_DIR)
            z.write(full_path, rel_path)
            files_added += 1

import shutil
shutil.copy2(OUT_ZIP, OUT_ZIP_RELEASE)

print(f"[OK] Archive complete generee avec succes ({files_added} fichiers inclus) !")
print(f"     -> {OUT_ZIP}")
print(f"     -> {OUT_ZIP_RELEASE}")
