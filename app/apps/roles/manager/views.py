from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.cms import models as cms_models

@login_required
def index(request):
    settings = cms_models.Settings.objects.first()
    return render(request, 'pages/manager/others/index.html',locals())


