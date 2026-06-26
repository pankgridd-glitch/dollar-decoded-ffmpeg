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
            return jsonify({"error": "audio missing"}), 400

        # Multiple Pexels clips fetch karo
        r = requests.get(
            "https://api.pexels.com/videos/search?query=stock market finance money investing&per_page=10",
            headers={"Authorization": pexels_key}, timeout=15
        )
        videos = r.json().get('videos', [])

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = f"{tmp}/audio.mp3"
            output_path = f"{tmp}/out.mp4"
            audio_file.save(audio_path)

            # Audio duration pata karo
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries',
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ], capture_output=True, text=True)
            audio_duration = float(result.stdout.strip())

            # Clips download karo jab tak audio duration cover na ho
            clip_paths = []
            total_duration = 0
            clip_num = 0

            for v in videos:
                if total_duration >= audio_duration:
                    break
                for vf in v.get('video_files', []):
                    if vf.get('width', 0) >= 1280 and vf.get('height', 0) >= 720:
                        clip_path = f"{tmp}/clip_{clip_num}.mp4"
                        vr = requests.get(vf['link'], timeout=120, stream=True)
                        with open(clip_path, 'wb') as f:
                            for chunk in vr.iter_content(8192):
                                f.write(chunk)
                        
                        # Clip duration check
                        dr = subprocess.run([
                            'ffprobe', '-v', 'error', '-show_entries',
                            'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                            clip_path
                        ], capture_output=True, text=True)
                        clip_dur = float(dr.stdout.strip() or 0)
                        
                        clip_paths.append(clip_path)
                        total_duration += clip_dur
                        clip_num += 1
                        break

            if not clip_paths:
                return jsonify({"error": "No HD clips found"}), 500

            # Clips concat karo
            if len(clip_paths) == 1:
                bg_path = clip_paths[0]
            else:
                # Concat list file banao
                list_file = f"{tmp}/clips.txt"
                with open(list_file, 'w') as f:
                    for cp in clip_paths:
                        f.write(f"file '{cp}'\n")
                
                bg_path = f"{tmp}/bg_merged.mp4"
                subprocess.run([
                    'ffmpeg', '-f', 'concat', '-safe', '0',
                    '-i', list_file, '-c', 'copy', '-y', bg_path
                ], check=True, timeout=300)

            # Final merge — HD quality
            subprocess.run([
                'ffmpeg',
                '-stream_loop', '-1', '-i', bg_path,
                '-i', audio_path,
                '-c:v', 'libx264', '-preset', 'fast',
                '-crf', '23', '-vf', 'scale=1280:720',
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0', '-map', '1:a:0',
                '-t', str(audio_duration),
                '-y', output_path
            ], check=True, timeout=600)

            return send_file(output_path, mimetype='video/mp4',
                           as_attachment=True,
                           download_name=f"{title}.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
