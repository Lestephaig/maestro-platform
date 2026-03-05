from django.shortcuts import render

def home(request):
    """Главная страница платформы"""
    return render(request, 'home.html')


def support(request):
    """Страница поддержки и контактов"""
    return render(request, 'support.html')