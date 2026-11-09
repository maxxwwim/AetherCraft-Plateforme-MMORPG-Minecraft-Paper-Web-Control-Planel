import os
import sys
import glob
import subprocess
import zipfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

SRC_DIR = os.path.join(BASE_DIR, "plugins_src", "AetherVisuals", "src")
BIN_DIR = os.path.join(BASE_DIR, "plugins_src", "AetherVisuals", "bin")
OUT_JAR = os.path.join(BASE_DIR, "plugins", "AetherVisuals.jar")
ECJ_JAR = os.path.join(BASE_DIR, "cache", "ecj.jar")

# 0. Localisation dynamique de Java 21
candidate_java = os.path.join(BASE_DIR, "runtime", "jdk-21.0.13+9-jre", "bin", "java.exe")
if os.path.exists(candidate_java):
    JAVA_EXE = candidate_java
elif shutil.which("java"):
    JAVA_EXE = shutil.which("java")
else:
    JAVA_EXE = "java"

os.makedirs(BIN_DIR, exist_ok=True)
for old_cls in glob.glob(os.path.join(BIN_DIR, "**", "*.class"), recursive=True):
    try:
        os.remove(old_cls)
    except OSError:
        pass
os.makedirs(os.path.dirname(OUT_JAR), exist_ok=True)

# 1. Vérification et Initialisation Automatique de la DB SQLite
DB_PATH = os.path.join(BASE_DIR, "data", "aethercraft.db")
if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
    print(f"[*] Base de donnees introuvable ou vide : {DB_PATH}")
    print("[*] Initialisation automatique du schema SQLite et des tables...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    web_dir = os.path.join(ROOT_DIR, "web")
    if web_dir not in sys.path:
        sys.path.insert(0, web_dir)
    try:
        from services.database import init_database
        init_database()
        print(f"[OK] Base SQLite aethercraft.db generee et initialisee avec succes !")
    except Exception as e:
        print(f"[!] Avertissement initialisation DB: {e}")
else:
    print(f"[OK] Base de donnees SQLite existante et validee : {DB_PATH}")

# 2. Collecter le classpath
cp_jars = []
for p in [
    os.path.join(BASE_DIR, "versions", "1.21.1", "paper-1.21.1.jar"),
    os.path.join(BASE_DIR, "server.jar"),
    os.path.join(BASE_DIR, "paper-1.21.1-133.jar"),
    os.path.join(BASE_DIR, "plugins", "MapEngine-1.8.12-all.jar"),
    os.path.join(BASE_DIR, "plugins", "MapBrowser-1.0-beta3-all.jar")
]:
    if os.path.exists(p) and p not in cp_jars:
        cp_jars.append(p)

for root, dirs, files in os.walk(os.path.join(BASE_DIR, "libraries")):
    for f in files:
        if f.endswith(".jar"):
            cp_jars.append(os.path.join(root, f))

classpath = ";".join(cp_jars)

# 3. Collecter les sources Java
java_files = glob.glob(os.path.join(SRC_DIR, "**", "*.java"), recursive=True)
print(f"Compilation de {len(java_files)} classes Java...")

# 4. Exécuter ECJ
cmd = [
    JAVA_EXE,
    "-jar", ECJ_JAR,
    "-21",
    "-nowarn",
    "-cp", classpath,
    "-d", BIN_DIR,
] + java_files

result = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)

if result.returncode != 0:
    print("Compilation echouee !")
    sys.exit(1)

# 5. Empaqueter AetherVisuals.jar
print(f"Creation de {OUT_JAR}...")
plugin_yml_src = os.path.join(SRC_DIR, "plugin.yml")
plugin_yml_bin = os.path.join(BIN_DIR, "plugin.yml")

# Synchroniser plugin.yml source vers bin
if os.path.exists(plugin_yml_src):
    shutil.copy2(plugin_yml_src, plugin_yml_bin)

with zipfile.ZipFile(OUT_JAR, "w", zipfile.ZIP_DEFLATED) as z:
    # Ajouter plugin.yml une seule et unique fois
    if os.path.exists(plugin_yml_src):
        z.write(plugin_yml_src, "plugin.yml")

    # Ajouter les ressources (.png, .jpg, etc.) depuis SRC_DIR
    for root, dirs, files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".java") or f.lower() == "plugin.yml":
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, SRC_DIR)
            z.write(full_path, rel_path)

    # Ajouter les .class compilés (en ignorant tout doublon de plugin.yml)
    for root, dirs, files in os.walk(BIN_DIR):
        for f in files:
            if f.lower() == "plugin.yml":
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, BIN_DIR)
            z.write(full_path, rel_path)

print("AetherVisuals.jar cree avec succes !")
