import os
import time
from shared.utils import anonymiser_fichier

FOLDER_SHARED = os.environ.get("FOLDER_SHARED", "./shared")
UPLOAD_FOLDER = os.path.join(FOLDER_SHARED, "uploads")

print("🔄 OCR Worker démarré")

while True:
    fichiers = [f for f in os.listdir(UPLOAD_FOLDER) if not f.endswith(".done") and os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
    for fichier in fichiers:
        chemin = os.path.join(UPLOAD_FOLDER, fichier)
        print(f"🛠 Traitement du fichier : {fichier}")
        try:
            anonymiser_fichier(chemin)
            os.rename(chemin, chemin + ".done")
            print(f"✅ Terminé : {fichier}")
        except Exception as e:
            print(f"❌ Erreur : {fichier} → {e}")
    time.sleep(5)