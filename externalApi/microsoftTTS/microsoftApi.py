from django.conf import settings
import azure.cognitiveservices.speech as speechsdk


def generateSound(text,config,outFilePath,retry=2):
    try:
        for _index in range(retry):
            speech_config = speechsdk.SpeechConfig(subscription=settings.AZURE_SECRET_KEY,region=settings.AZURE_REGION)
            speech_config.speech_synthesis_voice_name=config

            if outFilePath.split('.')[-1].lower() == 'wav':
                audio_config = speechsdk.audio.AudioOutputConfig(filename=outFilePath)
            else:
                speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
                audio_config = speechsdk.audio.AudioOutputConfig(filename=outFilePath)

            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = speech_synthesizer.speak_text_async(text).get()
            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
        return False
    except:
        return 0
            