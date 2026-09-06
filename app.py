import os
import re
import glob
import requests
from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def get_yt_dlp_options(url):
    cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
    
    opts = {
        'format': 'best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
    }

    # YouTube ဖြစ်ပါက Bot Bypass Settings သီးသန့်ထည့်သွင်းခြင်း
    if 'youtube.com' in url or 'youtu.be' in url:
        opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        })
        if os.path.exists(cookie_path):
            opts['cookiefile'] = cookie_path

    return opts

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-info', methods=['POST'])
@app.route('/download', methods=['POST'])
@app.route('/fetch', methods=['POST'])
def process_video():
    data = request.get_json(silent=True) or request.form
    video_url = data.get('url', '').strip()

    if not video_url:
        return jsonify({'success': False, 'error': 'URL ထည့်သွင်းပေးပါ'}), 400

    ydl_opts = get_yt_dlp_options(video_url)

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

            return jsonify({
                'success': True,
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'download_url': f'/get-file/{actual_filename}',
                'url': f'/get-file/{actual_filename}',
                'formats': [
                    {
                        'quality': 'HD Video (MP4)',
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
