from django.shortcuts import render, get_object_or_404
from .models import PerformerProfile

def performer_detail(request, performer_id):
    """Страница детальной информации об артисте"""
    performer = get_object_or_404(PerformerProfile, id=performer_id)
    context = {
        'performer': performer,
    }
    return render(request, 'performers/performer_detail.html', context)
