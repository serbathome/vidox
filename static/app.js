
var app = new Vue({
    el: '#root',
    delimiters: ['${', '}'],
    data: {
        jobs: [],
        fileSize: 0
    },
    methods: {
        drop: function (id) {
            axios.get(/delete/ + id)
                .then((response) => {
                    if (response.data.status == "ok") {
                        console.log("deleted successfully");
                    }
                    else {
                        console.log("error happened");
                    }
                    this.get();
                });
            return false;
        },
        run: function (id) {
            axios.get(/transcribe/ + id)
                .then((response) => {
                    if (response.data.status == "ok") {
                        this.pushNotification('Success', 'Transcription started', 'success');
                        console.log("scheduled successfully");
                    }
                    else {
                        this.pushNotification('Error', 'Transcription failed', 'error');
                        console.log("error happened");
                    }
                    this.get();
                });
            return false;
        },
        get: function () {
            this.jobs = [];
            axios.get('/refresh')
                .then((response) => {
                    response.data.jobs.forEach(element => {
                        transcript = 'not ready';
                        if (element.status == 'ready') {
                            transcript = `/${element.id}.txt`;
                        }
                        this.jobs.push(
                            {
                                'id': element.id,
                                'filename': element.filename,
                                'status': element.status,
                                'language': element.language
                            }
                        );
                    });
                });
        },
        updateProgress: function (progressEvent) {
            progress = Math.round((progressEvent.loaded / fileSize) * 100);
            document.getElementById("progress").style["width"] = progress + "%";
            if (progress == 100) {
                document.getElementById("progress").classList.remove("progress-bar-animated");
            }
            else {
                document.getElementById("progress").classList.add("progress-bar-animated");
            }
        },
        uploadFile: function () {
            lang = document.getElementById("language").value;
            document.getElementById("progress").style["width"] = "0%";
            var formData = new FormData();
            var imagefile = document.querySelector('#file');
            fileSize = imagefile.files[0].size;
            formData.append("file", imagefile.files[0]);
            formData.append("language", lang)
            axios.post('/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                onUploadProgress: progressEvent => this.updateProgress(progressEvent),
            })
                .then((response) => {
                    this.get();
                });
            return false;
        },
        download: function (id) {
            axios.get(/download/ + id)
                .then((response) => {
                    if (response.data.status == "ok") {
                        console.log(response.data.text);
                    }
                    else {
                        console.log("error happened");
                    }
                    this.get();
                });
            return false;
        },
        pushNotification: function (title, message, status) {
            new Notify({
                status: status,
                title: title,
                text: message,
                effect: 'fade',
                speed: 300,
                customClass: null,
                customIcon: null,
                showIcon: true,
                showCloseButton: true,
                autoclose: true,
                autotimeout: 3000,
                gap: 20,
                distance: 20,
                type: 1,
                position: 'right top'
            })
        }
    },
    mounted: function () {
        this.get();
    }
})