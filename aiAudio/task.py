from celery import shared_task
from utils.common import executeCommand
from django.db import connection


@shared_task(bind=True)
def convertMp3AudioToWav(self,audioData):
    connection.close()
    _inputP = audioData["inputPath"]
    _outputP = audioData["outputPath"]
    _ffmpegCommand = ["ffmpeg","-y","-i",_inputP,_outputP]
    _res = executeCommand(_ffmpegCommand)
    return True