import os
import polib
import requests
import json
import concurrent.futures

from flask import Flask, render_template, request, jsonify
from flask import send_file


app = Flask(__name__)

# Function to translate a single entry in a PO file
def translate_entry(entry, source_lang, target_lang):
    # Get translation from Google Translate API
    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": entry.msgid,
        }
    )

    # Extract translated text from response
    if response.status_code == 200:
        translations = json.loads(response.text)
        translation = translations[0][0][0]
    else:
        translation = ""

    # Update entry with translated text
    entry.msgstr = translation

    return entry

# Function to translate a PO or TXT file
def translate_file(file_path, source_lang, target_lang):
    # Read file into PO object
    if file_path.endswith(".po"):
        po = polib.pofile(file_path)
    elif file_path.endswith(".txt"):
        po = polib.POFile()

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                entry = polib.POEntry(msgid=line.strip())
                po.append(entry)
    else:
        return "Invalid file type"

    # Translate entries in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        entries = [entry for entry in po]
        results = [executor.submit(translate_entry, entry, source_lang, target_lang) for entry in entries]
        concurrent.futures.wait(results)

    # Write translated PO to disk
    output_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{os.path.splitext(os.path.basename(file_path))[0]}_{target_lang}.txt")
    po.save(output_path)

    return "Translation complete"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/translate", methods=["POST"])
def translate():
    # Get uploaded file
    file = request.files["file"]

    # Get source and target languages
    source_lang = request.form["source_lang"]
    target_lang = request.form["target_lang"]

    # Set output file name
    output_file = f"{os.path.splitext(os.path.basename(file.filename))[0]}_{target_lang}{os.path.splitext(file.filename)[1]}"

    # Save uploaded file to disk
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))

    # Translate file
    result = translate_file(os.path.join(app.config["UPLOAD_FOLDER"], file.filename), source_lang, target_lang)

    # Check for errors
    if result != "Translation complete":
        return jsonify({"error": result})

    # Return translated file
    return send_file(os.path.join(app.config["UPLOAD_FOLDER"], output_file))

if __name__ == "__main__":
    app.config["UPLOAD_FOLDER"] = "uploads"
    app.run(debug=True)
