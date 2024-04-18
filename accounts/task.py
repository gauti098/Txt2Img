from celery import shared_task,states
from celery import exceptions
from django.template.loader import render_to_string
from django.core.mail.message import EmailMultiAlternatives
from django.db import connection

@shared_task(bind=True)
def sendMail(self,data,asTemplate=True):
    connection.close()
    try:
        _fromEmail = data["fromEmail"]
        _toEmail = data["toEmail"]
        _bccEmail = data.get("bccEmail",None)

        if asTemplate:
            _templateContent = data["templateContent"]
            _templatePrefix = data["templatePrefix"]
            textContent = render_to_string(f'{_templatePrefix}.txt', _templateContent)
            htmlContent = render_to_string(f'{_templatePrefix}.html', _templateContent)
            subject = render_to_string(f'{_templatePrefix}_subject.txt',_templateContent).strip()
            if _bccEmail:
                msg = EmailMultiAlternatives(subject, textContent, _fromEmail, [_toEmail],bcc=[_bccEmail])
            else:
                msg = EmailMultiAlternatives(subject, textContent, _fromEmail, [_toEmail])
            print(textContent,htmlContent)
            msg.attach_alternative(htmlContent, 'text/html')
            msg.send()
        return True
    except Exception as e:
        self.update_state(
            state = states.FAILURE,
            meta = f"{e}"
        )
        raise exceptions.Ignore()

