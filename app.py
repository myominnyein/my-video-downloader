import os
import uuid
from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# Downloaded files ယာယီသိမ်းဆည်းမည့် folder
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        video_url = request.form.get("url")
        if not video_url:
            return render_template("index.html", error="URL ထည့်သွင်းပေးပါ။")

        try:
            # File name collision မဖြစ်စေရန် unique ID သုံးခြင်း
            file_id = str(uuid.uuid4())
            out_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

            ydl_opts = {
                "format": "best[ext=mp4]/best", # MP4 format အကြည်ဆုံးကို ဦးစားပေးယူမည်
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                title = info.get("title", "video")
                ext = info.get("ext", "mp4")

            # Download ပြီးပါက server ပေါ်မှ file ကို ပြန်ဖျက်ရန်
            @after_this_request
            def cleanup(response):
                try:
                    if os.path.exists(downloaded_file):
                        os.remove(downloaded_file)
                except Exception as e:
                    app.logger.error(f"Error removing file: {e}")
                return response

            # Clean download file name သတ်မှတ်ပေးခြင်း
            safe_filename = f"{title}.{ext}".encode('ascii', 'ignore').decode('ascii') or f"video.{ext}"

            return send_file(
                downloaded_file,
                as_attachment=True,
                download_name=safe_filename
            )

        except Exception as e:
            return render_template("index.html", error=f"Download ပြုလုပ်၍ မရပါ: {str(e)}")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
