import os
import uuid
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

# Create 'uploads' folder if it doesn't exist
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ----------------------------
# 1. File Upload Route
# ----------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(filepath)

    # Return URL relative to the server root. 
    # e.g. '/uploads/abcd-file.mp3'
    file_url = f"/uploads/{unique_filename}"
    return jsonify({"url": file_url})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    # Serves files from the uploads folder
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ----------------------------
# 2. Remix/Editing Route
# ----------------------------
@app.route("/remix", methods=["POST"])
def remix():
    """
    Expects JSON like:
    {
      "clips": [
        {
          "url": "/uploads/abc.mp3",
          "trimStart": 0,
          "trimEnd": 10,
          "speed": 1.0
        },
        ...
      ],
      "backgroundMusic": "/uploads/some_bg.mp3"  (optional)
    }
    """
    data = request.get_json()
    if not data or "clips" not in data:
        return jsonify({"error": "No clips data provided"}), 400

    clips = data["clips"]
    background_music_url = data.get("backgroundMusic")

    combined = None

    try:
        # -----------------------------
        # 2A. Process each clip
        # -----------------------------
        for clip_info in clips:
            url = clip_info["url"].lstrip("/")
            filepath = os.path.join(os.getcwd(), url)
            if not os.path.exists(filepath):
                return jsonify({"error": f"File not found: {filepath}"}), 404

            segment = AudioSegment.from_file(filepath)

            # 1) Trim (in seconds => convert to ms)
            start_ms = int(clip_info.get("trimStart", 0) * 1000)
            end_ms = int(clip_info.get("trimEnd", len(segment) / 1000) * 1000)
            if end_ms > len(segment):
                end_ms = len(segment)
            segment = segment[start_ms:end_ms]

            # 2) Speed (pydub's speedup is best for speeds > 1.0)
            speed = clip_info.get("speed", 1.0)
            if speed > 1.0:
                # Use speedup for faster playback
                segment = segment.speedup(playback_speed=speed, crossfade=0)
            elif speed < 1.0:
                # Slowing down changes pitch. For a quick hack:
                # Adjust frame_rate, then restore original to keep duration change but pitch shift
                original_frame_rate = segment.frame_rate
                new_frame_rate = int(original_frame_rate * speed)
                segment = segment._spawn(segment.raw_data, overrides={
                    "frame_rate": new_frame_rate
                }).set_frame_rate(original_frame_rate)
                # This means pitch is lowered. True time-stretching is more advanced.

            # Accumulate
            if combined is None:
                combined = segment
            else:
                combined += segment

        # -----------------------------
        # 2B. Overlay background music
        # -----------------------------
        if background_music_url:
            bg_url = background_music_url.lstrip("/")
            bg_filepath = os.path.join(os.getcwd(), bg_url)
            if not os.path.exists(bg_filepath):
                return jsonify({"error": f"Background file not found: {bg_filepath}"}), 404

            bg_segment = AudioSegment.from_file(bg_filepath)
            # Lower the background volume so the clips are clear
            bg_segment = bg_segment - 15

            # Loop the background track to match or exceed total length
            if len(bg_segment) < len(combined):
                loop_count = int(len(combined) / len(bg_segment)) + 1
                bg_segment = bg_segment * loop_count

            bg_segment = bg_segment[: len(combined)]

            # Overlay the combined vocal/clip track on top of background
            final_audio = bg_segment.overlay(combined)
        else:
            final_audio = combined

        # -----------------------------
        # 2C. Export & Send
        # -----------------------------
        output_filename = f"{uuid.uuid4().hex}_remix.mp3"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        final_audio.export(output_path, format="mp3")

        return send_file(output_path, as_attachment=True, download_name="remix.mp3")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 3. Run (for local dev)
# ----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
