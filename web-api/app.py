import os
import time
import fitz
from flask import Flask, render_template, request, send_from_directory, flash, url_for, session, redirect
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from shared.utils import anonymiser_fichier
load_dotenv()

app = Flask(__name__)
app.secret_key = 'xpert-ia-secret'

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FOLDER_SHARED = os.path.join(BASE_DIR, "shared")
UPLOAD_FOLDER = os.path.join(FOLDER_SHARED, "uploads")
RESULT_FOLDER = os.path.join(FOLDER_SHARED, "fichiers_anonymises")


ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.edi'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def generer_synthese_llm(fichiers_anonymises, dossier=RESULT_FOLDER):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    contenu = ""

    for fichier in fichiers_anonymises:
        path = os.path.join(dossier, fichier)
        ext = os.path.splitext(fichier)[1].lower()

        if ext in {".txt", ".edi"}:
            with open(path, "r", encoding="utf-8") as f:
                contenu += f.read() + "\n\n"
        elif ext == ".pdf":
            doc = fitz.open(path)
            contenu += "\n".join([page.get_text() for page in doc]) + "\n\n"
            doc.close()

    prompt = f"""
Voici des documents anonymisés :

{contenu[:3000]}

Génère une synthèse professionnelle et structurée comportant et ignorer les données personnelles :
- Présentation claire avec titres ou bullet points si pertinent

Langue : Français
"""
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return completion.choices[0].message.content

@app.route("/", methods=["GET", "POST"])
def index():
    if "historique_fichiers" not in session:
        session["historique_fichiers"] = []

    nouveaux_fichiers = []
    synthese = ""

    if request.method == "POST":
        files = request.files.getlist("files[]")
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                chemin_upload = os.path.join(UPLOAD_FOLDER, filename)
                file.save(chemin_upload)

                # 🔄 Appliquer anonymisation et récupérer le chemin du fichier anonymisé
                chemin_sortie = anonymiser_fichier(chemin_upload)
                if chemin_sortie and os.path.exists(chemin_sortie):
                    nom_anonymise = os.path.basename(chemin_sortie)
                    nouveaux_fichiers.append(nom_anonymise)
                    print(f"✅ Fichier anonymisé ajouté : {nom_anonymise}")
                else:
                    print("⚠️ Aucun fichier anonymisé généré pour :", filename)

        historique = set(session.get("historique_fichiers", []))
        historique.update(nouveaux_fichiers)
        session["historique_fichiers"] = list(historique)

        if nouveaux_fichiers:
            try:
                synthese = generer_synthese_llm(nouveaux_fichiers)
            except Exception as e:
                synthese = "Erreur lors de la synthèse IA : " + str(e)

    fichiers_actuels = sorted(os.listdir(RESULT_FOLDER))
    print("📁 Fichiers dans RESULT_FOLDER :", fichiers_actuels)
    return render_template("index.html", fichiers=fichiers_actuels, synthese=synthese)

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(RESULT_FOLDER, filename, as_attachment=True)

@app.route("/delete/<filename>")
def delete_file(filename):
    file_path = os.path.join(RESULT_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f"Le fichier '{filename}' a été supprimé.", "success")
    else:
        flash(f"Le fichier '{filename}' est introuvable.", "danger")

    if "historique_fichiers" in session and filename in session["historique_fichiers"]:
        session["historique_fichiers"].remove(filename)

    return redirect(url_for('index'))

@app.route("/reset")
def reset():
    for f in os.listdir(RESULT_FOLDER):
        os.remove(os.path.join(RESULT_FOLDER, f))
    session["historique_fichiers"] = []
    flash("Historique réinitialisé avec succès.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

