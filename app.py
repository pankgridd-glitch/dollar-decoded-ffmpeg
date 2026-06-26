from flask import Flask, request, jsonify
import subprocess, os, requests, tempfile, threading

app = Flask(__name__)

def process_and_upload(audio_data, title, pexels_key, youtube_token):
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search?query=stock market finance money&per_page=5",
            headers={"Authorization": pexels_key}, timeout=15
        )
        videos = r.json().get('videos', [])
        
        video_url = None
        for v in videos:
            for vf in v.get('video_files', []):
                if vf.get('width', 0) >= 1280:
                    video_url = vf['link']
                    break
            if video_url:
                break

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = f"{tmp}/audio.mp3"
            video_path = f"{tmp}/bg.mp4"
            output_path = f"{tmp}/out.mp4"

            with open(audio_path, 'wb') as f:
                f.write(audio_data)

            vr = requests.get(video_url, timeout=120, stream=True)
            with open(video_path, 'wb') as f:
                for chunk in vr.iter_content(8192):
                    f.write(chunk)

            # Audio duration
            dr = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries',
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ], capture_output=True, text=True)
            duration = dr.stdout.strip()

            subprocess.run([
                'ffmpeg',
                '-stream_loop', '-1', '-i', video_path,
                '-i', audio_path,
                '-c:v', 'libx264', '-preset', 'ultrafast',
                '-crf', '28', '-vf', 'scale=1280:720',
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0', '-map', '1:a:0',
                '-t', duration,
                '-y', output_path
            ], check=True, timeout=600)

            # YouTube upload
            with open(output_path, 'rb') as f:
                video_data = f.read()

            headers = {"Authorization": f"Bearer {youtube_token}"}
            meta = {
                "snippet": {"title": title, "categoryId": "27"},
                "status": {"privacyStatus": "public"}
            }
            
            init_r = requests.post(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                headers={**headers, "Content-Type": "application/json",
                         "X-Upload-Content-Type": "video/mp4",
                         "X-Upload-Content-Length": str(len(video_data))},
                json=meta
            )
            
            upload_url = init_r.headers.get('Location')
            requests.put(upload_url,
                        headers={"Content-Type": "video/mp4"},
                        data=video_data)

    except Exception as e:
        print(f"Background error: {e}")

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/create-video', methods=['POST'])
def create_video():
    audio_file = request.files.get('audio')
    title = request.form.get('title', 'Finance Video')
    youtube_token = request.form.get('youtube_token', '')
    pexels_key = os.environ.get('PEXELS_API_KEY', '')

    if not audio_file:
        return jsonify({"error": "audio missing"}), 400

    audio_data = audio_file.read()

    # Background thread mein chalo
    t = threading.Thread(
        target=process_and_upload,
        args=(audio_data, title, pexels_key, youtube_token)
    )
    t.daemon = True
    t.start()

    # Turant response do — Make.com timeout nahi hoga
    return jsonify({"status": "processing", "message": "Video being created"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
