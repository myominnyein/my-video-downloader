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
    """Render/Cloud IP ပေါ်တွင် YouTube bot block ကျော်လွှားရန် options များ"""
    cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
    
    opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s_%(title).50s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        # Server IP block ကို ကျော်လွှားရန် iOS / TV embedded client သုံးခြင်း
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
    
    # cookies.txt ရှိပါက auto အသုံးပြုရန်
    if os.path.exists(cookie_path):
        opts['cookiefile'] = cookie_path
        
    return opts

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json() if request.is_json else request.form
    video_url = data.get('url', '').strip()

    if not video_url:
        return jsonify({'success': False, 'error': 'URL ထည့်သွင်းပေးပါ'}), 400

    ydl_opts = get_yt_dlp_options()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Video အချက်အလက်ယူခြင်းနှင့် download ဆွဲခြင်း
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)

            # Extension ပြောင်းလဲမှုရှိပါက ဖိုင်ပြန်ရှာခြင်း
            if not os.path.exists(filename):
                base_name = os.path.splitext(filename)[0]
                matching_files = glob.glob(f"{glob.escape(base_name)}.*")
                if matching_files:
                    filename = matching_files[0]

            actual_filename = os.path.basename(filename)

            return jsonify({
                'success': True,
                'title': info.get('title', 'Video'),
                'download_url': f'/get-file/{actual_filename}'
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-file/<filename>')
def get_file(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
