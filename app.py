
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from moviepy import editor
import requests
import boto3

UPLOAD_FOLDER = '.'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'thisismysecretcode'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://///Users/serb/sources/vidox/test.db'
db = SQLAlchemy(app)


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(80), unique=False, nullable=False)
    yandex_id = db.Column(db.String(64), unique=True, nullable=True)
    status = db.Column(db.String(10), unique=False, nullable=False)
    text = db.Column(db.String(4294000000), unique=False, nullable=True)

    def __str__(self):
        return f"{self.id}/{self.filename}/{self.yandex_id}/{self.status}"


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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'status': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'No selected file'})
        if file and allowed_file(file.filename):
            print("saving file")
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("file saved")
            job = Job()
            job.filename = filename
            job.status = 'uploaded'
            db.session.add(job)
            db.session.commit()
            return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "wrong method"})


@app.route('/refresh')
def refresh():
    jobs = []
    for j in Job.query.order_by(Job.id).all():
        if j.status == "scheduled":
            print(f"found a scheduled request {j.yandex_id}")
            GET = f"https://operation.api.cloud.yandex.net/operations/{j.yandex_id}"
            key = os.getenv('s3key')
            header = {'Authorization': 'Api-Key {}'.format(key)}
            req = requests.get(GET.format(id=id), headers=header)
            print(f"got response{req}")
            req = req.json()
            text = []
            if req['done']:
                print("found status of done")
                for chunk in req['response']['chunks']:
                    if chunk['channelTag'] == '1':
                        text.append(chunk['alternatives'][0]['text'])
                j.text = '\n'.join(text)
                j.status = "ready"
                db.session.commit()
        jobs.append(
            {
                'id': j.id,
                'filename': j.filename,
                'status': j.status
            }
        )
    return jsonify({'jobs': jobs})


@app.route('/delete/<int:job_id>')
def delete(job_id):
    j = Job.query.filter_by(id=job_id).first()
    if j is not None:
        db.session.delete(j)
        db.session.commit()
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error"})


@app.route('/download/<int:job_id>')
def download(job_id):
    j = Job.query.filter_by(id=job_id).first()
    if j is not None:
        text = j.text
        filename = str(job_id) + ".txt"
        with open(filename, 'w') as f:
            f.write(text)
        return send_file(filename, as_attachment=True)
    else:
        return "OK"


@app.route('/transcribe/<int:job_id>')
def transcribe(job_id):
    j = Job.query.filter_by(id=job_id).first()
    if j.status == 'uploaded':
        filename = j.filename
        print(f"processing filename {filename}")
        video = editor.VideoFileClip(filename=filename)
        audio = video.audio
        audio.write_audiofile(filename=filename + ".mp3",
                              verbose=False, logger=None)
        print("audio track extracted")
        print("uploading to yandex s3")
        uploadFile(filename + ".mp3")
        print("upload completed")
        print("requesting voice recognition")
        key = os.getenv('s3key')
        filelink = 'https://storage.yandexcloud.net/vidox/' + filename + '.mp3'
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
        print(f"job posted with id {id}")
        j.yandex_id = id
        j.status = "scheduled"
        db.session.commit()
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'error'})
