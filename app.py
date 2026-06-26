from flask import Flask, request, jsonify, send_file
import subprocess, os, requests, tempfile, logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/create-video', methods=['POST'])
def create_video():
    try:
        data = request.json
        audio_url = data.get('audio_url')
        title = data.get('title', 'video')
        pexels_key = os.environ.get('PEXELS_API_KEY', '')

        # Pexels video fetch
        r = requests.get(
            "https://api.pexels.com/videos/search?query=stock market finance money&per_page=5",
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

            # Download audio
            with open(audio_path, 'wb') as f:
                f.write(requests.get(audio_url, timeout=60).content)

            # Download video
            with open(video_path, 'wb') as f:
                vr = requests.get(video_url, timeout=120, stream=True)
                for chunk in vr.iter_content(8192):
                    f.write(chunk)

            # FFmpeg merge
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
        app.logger.error(f"ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
