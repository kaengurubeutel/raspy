from django.shortcuts import render

# Create your views here.
from django.http import Http404, HttpResponse
from django.conf import settings
from django.utils.http import http_date
import os
from datetime import datetime

def media_file_response(request, path):
    media_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(media_path):
        with open(media_path, 'rb') as f:
            content = f.read()
            response = HttpResponse(content, content_type="audio/wav")
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Last-Modified'] = http_date(os.path.getmtime(media_path))
            return response
    else:
        raise Http404("Datei nicht gefunden")