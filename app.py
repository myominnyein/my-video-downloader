import os
import re
import glob
import requests
from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

# Video သိမ်းဆည်းမည့် Downloads Folder
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def get_yt_dlp_options():
    cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
    opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s_%(title).50s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'tv_embedded', 'mweb'],
                'player_skip': ['webpage', 'configs', 'js']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.ios.youtube/19.45.4 (iPhone16,2; U; CPU iOS 18_1 like Mac OS X; en_US)',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    if os.path.exists(cookie_path):
        opts['cookiefile'] = cookie_path
    return opts

@app.route('/')
def index():
    return render_template('index.html')

# Frontend က Fetch လုပ်သည့် route အားလုံးကို လက်ခံရန်
@app.route('/get-info', methods=['POST'])
@app.route('/download', methods=['POST'])
@app.route('/fetch', methods=['POST'])
def process_video():
    data = request.get_json(silent=True) or request.form
    video_url = data.get('url', '').strip()

    if not video_url:
        return jsonify({'success': False, 'error': 'URL ထည့်သွင်းပေးပါ'}), 400

    ydl_opts = get_yt_dlp_options()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                base_name = os.path.splitext(filename)[0]
                matching_files = glob.glob(f"{glob.escape(base_name)}.*")
                if matching_files:
                    filename = matching_files[0]

            actual_filename = os.path.basename(filename)

            # Frontend က မျှော်လင့်နိုင်သော format မျိုးစုံဖြင့် ပြန်လည်ပို့ပေးခြင်း
            return jsonify({
                'success': True,
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'download_url': f'/get-file/{actual_filename}',
                'url': f'/get-file/{actual_filename}',
                'formats': [
                    {
                        'quality': 'HD Video',
                        'url': f'/get-file/{actual_filename}',
                        'ext': 'mp4'
                    }
                ]
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-file/<filename>')
def get_file(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
