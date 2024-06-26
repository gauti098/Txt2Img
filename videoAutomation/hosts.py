from django.conf import settings
from django_hosts import patterns, host

print(settings.ROOT_URLCONF)
host_patterns = patterns('',
    host(r'www', settings.ROOT_URLCONF, name='www'),
    host(r'api', 'backgroundclip.urls', name='api'),
    host(r'(\w+)', 'path.to.custom_urls', name='wildcard'),
)