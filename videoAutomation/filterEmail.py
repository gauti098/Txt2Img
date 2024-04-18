from django.http import UnreadablePostError
import logging

logger = logging.getLogger(__name__)


class FilterErrorEmail(logging.Filter):
     def filter(self, record):
         if record.msg.find('Invalid HTTP_HOST header')!= -1:
             return False
         return True
