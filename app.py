import os
import uuid
from flask import Flask, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Set up uploads folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Create a secure, unique filename
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(filepath)

    # Return a URL to access the file (relative to the server)
    file_url = f"/uploads/{unique_filename}"
    return jsonify({"url": file_url})

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/remix", methods=["POST"])
def remix():
    data = request.get_json()
    if not data or "urls" not in data:
        return jsonify({"error": "No file URLs provided"}), 400


    urls = data["urls"]
    combined = None

    try:
        # Concatenate all audio clips in the provided order
        for url in urls:
            # Expecting URL format like "/uploads/filename.ext"
            filename = url.lstrip("/")
            filepath = os.path.join(os.getcwd(), filename)
            if not os.path.exists(filepath):
                return jsonify({"error": f"File not found: {filepath}"}), 404

            segment = AudioSegment.from_file(filepath)
            if combined is None:
                combined = segment
            else:
                combined += segment

        # If background music is provided, overlay it
        background_music_url = data.get("backgroundMusic")
        if background_music_url:
            bg_filename = background_music_url.lstrip("/")
            bg_filepath = os.path.join(os.getcwd(), bg_filename)
            if not os.path.exists(bg_filepath):
                return jsonify({"error": f"Background file not found: {bg_filepath}"}), 404

            bg_segment = AudioSegment.from_file(bg_filepath)
            # Lower the background volume
            bg_segment = bg_segment - 15  
            # Loop the background track to cover the entire combined duration
            loop_count = int(len(combined) / len(bg_segment)) + 1
            bg_loop = bg_segment * loop_count
            bg_loop = bg_loop[:len(combined)]
            # Overlay the voice clips on top of the background music
            final_audio = bg_loop.overlay(combined)
        else:
            final_audio = combined

        # Export the final remix to a new file
        output_filename = f"{uuid.uuid4().hex}_remix.mp3"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        final_audio.export(output_path, format="mp3")
        return send_file(output_path, as_attachment=True, download_name="remix.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
