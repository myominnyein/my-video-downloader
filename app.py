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

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_tiktok_data(url):
    api_url = f"https://www.tikwm.com/api/?url={url}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(api_url, headers=headers, timeout=15)
    data = response.json()
    if data.get('code') == 0:
        return data.get('data')
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-info', methods=['POST'])
def get_info():
    url = request.json.get('url', '').strip()
    if not url:
        return jsonify({'error': 'Link ထည့်ပေးပါ'}), 400

    # TikTok Info
    if "tiktok.com" in url.lower():
        try:
            tk_data = get_tiktok_data(url)
            if tk_data:
                return jsonify({
                    'platform': 'tiktok',
                    'title': tk_data.get('title', 'TikTok Video'),
                    'thumbnail': tk_data.get('cover', ''),
                    'duration': f"{tk_data.get('duration', 0)}s",
                    'uploader': tk_data.get('author', {}).get('nickname', 'TikTok Creator'),
                    'qualities': ['1080p / HD (No Watermark)', 'Audio Only (MP3)']
                })
            return jsonify({'error': 'TikTok ဗီဒီယို ရှာမတွေ့ပါ'}), 404
        except Exception as e:
            return jsonify({'error': f'TikTok Error: {str(e)}'}), 500

    # YouTube Info (Standard High-Quality Options အမြဲ ထည့်ပေးခြင်း)
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # User အမြဲရွေးချယ်နိုင်စေရန် Full Options စာရင်းပေးခြင်း
            qualities = [
                '1080p Full HD',
                '720p HD',
                '480p SD',
                '360p Low',
                'Audio Only (MP3)'
            ]

            return jsonify({
                'platform': 'youtube',
                'title': info.get('title', 'YouTube Video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration_string', 'N/A'),
                'uploader': info.get('uploader', 'YouTube Creator'),
                'qualities': qualities
            })
    except Exception as e:
        return jsonify({'error': f'YouTube Error: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url', '').strip()
    quality = data.get('quality', '1080p Full HD')

    if not url:
        return jsonify({'error': 'Link ထည့်ပေးပါ'}), 400

    # TikTok Download Handler
    if "tiktok.com" in url.lower():
        try:
            tk_data = get_tiktok_data(url)
            if not tk_data:
                return jsonify({'error': 'TikTok ဒေါင်းလုဒ် link ယူမရပါ'}), 500

            is_mp3 = "Audio" in quality or "MP3" in quality
            download_link = tk_data.get('music') if is_mp3 else (tk_data.get('hdplay') or tk_data.get('play'))
            ext = 'mp3' if is_mp3 else 'mp4'
            
            video_id = tk_data.get('id', 'tiktok_video')
            title = clean_filename(tk_data.get('title', f'tiktok_{video_id}'))
            file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")

            r = requests.get(download_link, stream=True, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"{title}.{ext}",
                mimetype=f"{'audio' if is_mp3 else 'video'}/{ext}"
            )
        except Exception as e:
            return jsonify({'error': f'TikTok ဒေါင်းလုဒ် မအောင်မြင်ပါ: {str(e)}'}), 500

    # YouTube Download Handler (ရွေးထားသည့် Height အတိုင်း အကောင်းဆုံး ဆွဲယူခြင်း)
    try:
        is_mp3 = "Audio" in quality or "MP3" in quality

        if is_mp3:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            height_match = re.search(r'\d+', quality)
            target_h = height_match.group() if height_match else '1080'
            
            # ရွေးချယ်ထားသော Resolution အတိုင်း အကောင်းဆုံး Video + Audio ကို ပေါင်းစပ်ဆွဲယူခြင်း
            ydl_opts = {
                'format': f'bestvideo[height<={target_h}]+bestaudio/best[height<={target_h}]/best',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
                'merge_output_format': 'mp4',
            }

        ydl_opts.update({
            'quiet': True,
            'no_warnings': True,
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            title = clean_filename(info.get('title', 'video'))

        target_ext = 'mp3' if is_mp3 else 'mp4'
        matches = glob.glob(os.path.join(DOWNLOAD_DIR, f"{video_id}.*"))
        if matches:
            target_file = matches[0]
            return send_file(
                target_file,
                as_attachment=True,
                download_name=f"{title}.{target_ext}",
                mimetype=f"{'audio' if is_mp3 else 'video'}/{target_ext}"
            )
        return jsonify({'error': 'ဖိုင်သိမ်းဆည်းရာတွင် အမှားဖြစ်ပေါ်ခဲ့သည်'}), 500

    except Exception as e:
        return jsonify({'error': f'ဒေါင်းလုဒ် မအောင်မြင်ပါ: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)