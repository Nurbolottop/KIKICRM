from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.cms import models as cms_models
from apps.contacts import models as contacts_models
from apps.contacts import views as contacts_views


@login_required
def index(request):
    settings = cms_models.Settings.objects.first()
    return render(request, 'pages/system/others/index.html', locals())
