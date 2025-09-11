from django.shortcuts import render, redirect
from django.contrib import messages
from apps.cms import models as cms_models
from apps.contacts import models as contacts_models
from apps.contacts import views as contacts_views
# Create your views here.

def index(request):
    settings = cms_models.Settings.objects.first()
    return render(request, 'pages/base/index.html', locals())