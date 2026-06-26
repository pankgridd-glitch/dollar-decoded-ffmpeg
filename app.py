from flask import Flask, request, jsonify, send_file
import subprocess, os, requests, tempfile

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/create-video', methods=['POST'])
def create_video():
    try:
        title = request.form.get('title', 'video')
        audio_file = request.files.get('audio')
        pexels_key = os.environ.get('PEXELS_API_KEY', '')

        if not audio_file:
            return jsonify({"error": "audio file missing"}), 400

        # Pexels video
        r = requests.get(
            "https://api.pexels.com/videos/search?query=stock market finance&per_page=5",
            headers={"Authorization": pexels_key}, timeout=15
        )
        videos = r.json().get('videos', [])
        video_url = None
        for v in videos:
            for vf in v.get('video_files', []):
                if vf.get('width', 0) >= 640:
                    video_url = vf['link']
                    break
            if video_url:
                break

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = f"{tmp}/audio.mp3"
            video_path = f"{tmp}/bg.mp4"
            output_path = f"{tmp}/out.mp4"

            # Save audio
            audio_file.save(audio_path)

            # Download video
            with open(video_path, 'wb') as f:
                vr = requests.get(video_url, timeout=120, stream=True)
                for chunk in vr.iter_content(8192):
                    f.write(chunk)

            # FFmpeg
            subprocess.run([
                'ffmpeg', '-i', video_path, '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac',
                '-map', '0:v:0', '-map', '1:a:0',
                '-shortest', '-y', output_path
            ], check=True, timeout=300)

            return send_file(output_path, mimetype='video/mp4',
                           as_attachment=True,
                           download_name=f"{title}.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
