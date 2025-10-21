from django.shortcuts import render

def home(request):
    """Главная страница платформы"""
    return render(request, 'home.html')