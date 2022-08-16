
from flask import Flask, render_template, request, flash, redirect
from werkzeug.utils import secure_filename
import os
from moviepy import editor
import requests
import time
import boto3

UPLOAD_FOLDER = '.'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mkv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'thisismysecretcode'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def uploadFile(filename):
    session = boto3.session.Session()
    s3 = session.client(
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )
    s3.upload_file(filename, 'vidox', filename)


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            context = {}
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("file saved")

            # We user moviepy to extract audio
            video = editor.VideoFileClip(filename=filename)
            audio = video.audio
            audio.write_audiofile(filename="result.mp3")

            # upload audio file to s3
            uploadFile('result.mp3')

            # Send audio file to Yandex Speech Recognition
            key = os.getenv('s3key')
            filelink = 'https://storage.yandexcloud.net/vidox/result.mp3'
            POST = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
            body = {
                "config": {
                    "specification": {
                        "languageCode": "ru-RU",
                        "audioEncoding": "MP3"
                    }
                },
                "audio": {
                    "uri": filelink
                }
            }
            header = {'Authorization': 'Api-Key {}'.format(key)}
            req = requests.post(POST, headers=header, json=body)
            data = req.json()
            id = data['id']
            while True:
                time.sleep(1)
                GET = "https://operation.api.cloud.yandex.net/operations/{id}"
                req = requests.get(GET.format(id=id), headers=header)
                req = req.json()
                if req['done']:
                    break
                print("Not ready")
            for chunk in req['response']['chunks']:
                if chunk['channelTag'] == '1':
                    print(chunk['alternatives'][0]['text'])

        return render_template('results.html', context=context)
    return render_template("index.html")
