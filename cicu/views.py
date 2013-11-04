from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_exempt
from django.core.files import File
from django.core.files.base import ContentFile

from PIL import Image
from os import remove, path, sep, makedirs

import math

from .forms import UploadedFileForm
from .models import UploadedFile
from .settings import IMAGE_CROPPED_UPLOAD_TO

from django.conf import settings

import cStringIO

import logging
logger = logging.getLogger('django.request')


@csrf_exempt
@xframe_options_exempt
@require_POST
def upload(request):
    form = UploadedFileForm(data=request.POST, files=request.FILES)
    if form.is_valid():
        uploaded_file = form.save()
        # pick an image file you have in the working directory
        # (or give full path name)
        try:
            img = Image.open(uploaded_file.file.path, mode='r')
        except NotImplementedError:
            img = Image.open(cStringIO.StringIO(uploaded_file.file.read()), mode='r')

        # get the image's width and height in pixels
        width, height = img.size
        data = {
            'path': uploaded_file.file.url,
            'id' : uploaded_file.id,
            'width' : width,
            'height' : height,
        }
        return HttpResponse(simplejson.dumps(data))
    else:
        return HttpResponseBadRequest(simplejson.dumps({'errors': form.errors}))

@csrf_exempt
@xframe_options_exempt
@require_POST
def crop(request):
    #try:
    if request.method == 'POST':
        box = request.POST.get('cropping', None)
        imageId = request.POST.get('id', None)

        try:
            uploaded_file = UploadedFile.objects.get(id=imageId)
        except UploadedFile.DoesNotExist:
            logger.error('Uploaded file does not exist: {0}'.format(imageId))
            return

        try:
            img = croppedImage = Image.open( uploaded_file.file.path, mode='r' )
        except:
            img = croppedImage = Image.open( cStringIO.StringIO(uploaded_file.file.read()), mode='r' )

        #import pdb;pdb.set_trace()
        values = [int(math.floor(float(x))) for x in box.split(',')]
        logger.info('Crop Values: %s'%values)

        width = abs(values[2] - values[0])
        height = abs(values[3] - values[1])

        if width and height and (width != img.size[0] or height != img.size[1]):
            logger.info('Crop values - w:%d h:%d maxW:%d maxH:%d' % (width, height, img.size[0], img.size[1],))
            try:
                croppedImage = img.crop(values).resize((width,height), Image.ANTIALIAS)
                logger.info('Croppped image %s'%croppedImage)
            except Exception as e:
                logger.error('Crop Exception: %s'%e)

        cropped_io = cStringIO.StringIO()
        
        croppedImage.save(cropped_io, format='JPEG') # save the image object

        cropped_file = UploadedFile.objects.create()

        cropped_file.file.save(uploaded_file.file.name, ContentFile(cropped_io.getvalue()))

        data = {
            'path': cropped_file.file.url,
            'id' : cropped_file.id,
        }

        return HttpResponse(simplejson.dumps(data))

    #except Exception, e:
    #   return HttpResponseBadRequest(simplejson.dumps({'errors': 'illegal request'}))
