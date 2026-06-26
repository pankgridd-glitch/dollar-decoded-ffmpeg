from flask import Flask, request, jsonify, send_file
import subprocess, os, requests, random, tempfile, logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok", "ffmpeg": "ready"})

@app.route('/create-video', methods=['POST'])
def create_video():
    try:
        data = request.json
        app.logger.info(f"Request received: {data}")
        
        audio_url = data.get('audio_url')
        title = data.get('title', 'Finance Video')

        if not audio_url:
            return jsonify({"error": "audio_url missing"}), 400

        # Pexels se video fetch
        headers = {"Authorization": PEXELS_KEY}
        r = requests.get(
            "https://api.pexels.com/videos/search?query=stock market money finance&per_page=5&orientation=landscape",
            headers=headers, timeout=15
        )
        r.raise_for_status()
        videos = r.json().get('videos', [])
        
        if not videos:
            return jsonify({"error": "No Pexels videos found"}), 500

        # HD video file dhundo
        video_url = None
        for v in videos:
            for vf in v.get('video_files', []):
                if vf.get('quality') in ['hd', 'sd'] and vf.get('width', 0) >= 640:
                    video_url = vf['link']
                    break
            if video_url:
                break

        if not video_url:
            video_url = videos[0]['video_files'][0]['link']

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = f"{tmp}/audio.mp3"
            video_path = f"{tmp}/bg.mp4"
            output_path = f"{tmp}/output.mp4"

            # Audio download
            app.logger.info(f"Downloading audio: {audio_url}")
            ar = requests.get(audio_url, timeout=60)
            ar.raise_for_status()
            with open(audio_path, 'wb') as f:
                f.write(ar.content)

            # Video download
            app.logger.info(f"Downloading video: {video_url}")
            vr = requests.get(video_url, timeout=120, stream=True)
            vr.raise_for_status()
            with open(video_path, 'wb') as f:
                for chunk in vr.iter_content(chunk_size=8192):
                    f.write(chunk)

            # FFmpeg
            app.logger.info("Running FFmpeg...")
            result = subprocess.run([
                'ffmpeg', '-i', video_path, '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac',
                '-map', '0:v:0', '-map', '1:a:0',
                '-shortest', '-y', output_path
            ], capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                app.logger.error(f"FFmpeg error: {result.stderr}")
                return jsonify({"error": "FFmpeg failed", "details": result.stderr}), 500

            app.logger.info("Video created successfully!")
            return send_file(output_path, mimetype='video/mp4',
                           as_attachment=True,
                           download_name=f"{title}.mp4")

    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
