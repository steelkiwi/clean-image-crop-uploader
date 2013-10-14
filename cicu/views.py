from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_exempt
from django.core.files import File

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
        pathToFile = path.join(settings.MEDIA_ROOT,IMAGE_CROPPED_UPLOAD_TO)
        box = request.POST.get('cropping', None)
        imageId = request.POST.get('id', None)

        uploaded_file = UploadedFile.objects.get(id=imageId)

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

                if not path.exists(pathToFile):
                    makedirs(pathToFile)
                    logger.info('Create dir %s'%pathToFile)

            except Exception as e:
                logger.error('Crop Exception: %s'%e)


        try:
            pathToFile = path.join(pathToFile, uploaded_file.file.path.split(sep)[-1])
            logger.info('Trying to save croppedimage to %s'%pathToFile)
        except:
            # save the crop locally
            pathToFile = path.join(settings.MEDIA_ROOT, uploaded_file.file.name)
            logger.info('No path to file, is probably an s3 image, saving to %s'%pathToFile)


        cropped_file = UploadedFile()
        
        croppedImage.save(pathToFile) # save the image object

        logger.info('Saved croppedimage to %s'%pathToFile)

        cropped_file_name = uploaded_file.file.name
        f = open(pathToFile, mode='r')
        cropped_file.file.save(cropped_file_name, File(f))
        f.close()
        remove(f.name) # clean up after ourselves


        data = {
            'path': cropped_file.file.url,
            'id' : cropped_file.id,
        }

        return HttpResponse(simplejson.dumps(data))

    #except Exception, e:
    #   return HttpResponseBadRequest(simplejson.dumps({'errors': 'illegal request'}))
