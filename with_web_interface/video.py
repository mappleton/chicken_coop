# import required modules

from flask import Blueprint, Response
import cv2
videoStreamBp = Blueprint('video_stream', __name__)

# Raspberry Pi camera module (requires picamera package)



def gen():
    camera = cv2.VideoCapture(0)

    while True:
        ret, img = camera.read()

        if ret:
            frame = cv2.imencode('.jpg', img)[1].tobytes()
            yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@videoStreamBp.route('/videopi')
def video_stream():
    return Response(gen(),mimetype='multipart/x-mixed-replace; boundary=frame')
