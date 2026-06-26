from flask import Flask, request, jsonify
import subprocess, os, requests, random, tempfile

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/create-video', methods=['POST'])
def create_video():
    data = request.json
    audio_url = data.get('audio_url')
    title = data.get('title', 'Finance Video')
    pexels_key = os.environ.get('PEXELS_API_KEY')
    
    # Pexels se finance video fetch karo
    headers = {"Authorization": pexels_key}
    r = requests.get(
        "https://api.pexels.com/videos/search?query=money finance stock market&per_page=10",
        headers=headers
    )
    videos = r.json()['videos']
    video_url = random.choice(videos)['video_files'][0]['link']
    
    with tempfile.TemporaryDirectory() as tmp:
        # Files download karo
        audio_path = f"{tmp}/audio.mp3"
        video_path = f"{tmp}/bg.mp4"
        output_path = f"{tmp}/output.mp4"
        
        # Audio download
        with open(audio_path, 'wb') as f:
            f.write(requests.get(audio_url).content)
        
        # Video download
        with open(video_path, 'wb') as f:
            f.write(requests.get(video_url).content)
        
        # FFmpeg merge
        subprocess.run([
            'ffmpeg', '-i', video_path, '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'aac',
            '-shortest', '-y', output_path
        ], check=True)
        
        # Output read karo
        with open(output_path, 'rb') as f:
            video_data = f.read()
    
    return video_data, 200, {
        'Content-Type': 'video/mp4',
        'Content-Disposition': f'attachment; filename="{title}.mp4"'
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
