from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
import json
from datetime import datetime, timedelta
from .models import PerformerProfile, PerformerAvailability, RepertoireItem
from .forms import RepertoireItemForm

def performer_detail(request, performer_id):
    """Страница детальной информации об артисте"""
    performer = get_object_or_404(PerformerProfile, id=performer_id)
    context = {
        'performer': performer,
    }
    return render(request, 'performers/performer_detail.html', context)


def specialists_list(request):
    """Страница со списком всех артистов"""
    performers = PerformerProfile.objects.select_related('user').all().order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(performers, 12)  # 12 артистов на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'performers': page_obj,
    }
    return render(request, 'performers/specialists_list.html', context)


@require_http_methods(["GET"])
def get_calendar_data(request, performer_id):
    """Получить данные календаря за месяц"""
    performer = get_object_or_404(PerformerProfile, id=performer_id)
    
    # Календарь доступен для всех пользователей
    
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))
    
    # Получить все отметки за месяц
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()
    
    availabilities = PerformerAvailability.objects.filter(
        performer=performer,
        date__gte=start_date,
        date__lt=end_date
    )
    
    # Форматировать данные
    data = {
        'calendar_mode': performer.calendar_mode,
        'availabilities': [
            {
                'date': avail.date.isoformat(),
                'status': avail.status,
                'notes': avail.notes
            }
            for avail in availabilities
        ]
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_availability(request, performer_id):
    """Обновить доступность на определенную дату"""
    performer = get_object_or_404(PerformerProfile, id=performer_id)
    
    # Проверка прав доступа
    if request.user != performer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        status = data.get('status')
        notes = data.get('notes', '')
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Если статус пустой, удаляем запись
        if not status or status == 'none':
            PerformerAvailability.objects.filter(
                performer=performer,
                date=date
            ).delete()
            return JsonResponse({'success': True, 'action': 'deleted'})
        
        # Иначе создаем или обновляем
        availability, created = PerformerAvailability.objects.update_or_create(
            performer=performer,
            date=date,
            defaults={
                'status': status,
                'notes': notes
            }
        )
        
        return JsonResponse({
            'success': True,
            'action': 'created' if created else 'updated',
            'data': {
                'date': availability.date.isoformat(),
                'status': availability.status,
                'notes': availability.notes
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_calendar_mode(request, performer_id):
    """Обновить режим календаря"""
    performer = get_object_or_404(PerformerProfile, id=performer_id)
    
    # Проверка прав доступа
    if request.user != performer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        mode = data.get('mode')
        
        if mode in ['mark_available', 'mark_unavailable']:
            performer.calendar_mode = mode
            performer.save()
            return JsonResponse({'success': True, 'mode': mode})
        else:
            return JsonResponse({'error': 'Invalid mode'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============= REPERTOIRE MANAGEMENT =============

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def add_repertoire_item(request):
    """Добавить произведение в репертуар"""
    if not hasattr(request.user, 'performer_profile'):
        return JsonResponse({'error': 'Not a performer'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        item = RepertoireItem.objects.create(
            performer=request.user.performer_profile,
            composer=data.get('composer', ''),
            work_title=data.get('work_title', ''),
            category=data.get('category', 'other'),
            epoch=data.get('epoch', ''),
            role_or_part=data.get('role_or_part', ''),
            year_performed=data.get('year_performed') or None,
            notes=data.get('notes', ''),
            video_link=data.get('video_link', ''),
            is_featured=data.get('is_featured', False),
        )
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'composer': item.composer,
                'work_title': item.work_title,
                'category': item.get_category_display(),
                'category_code': item.category,
                'epoch': item.get_epoch_display() if item.epoch else '',
                'role_or_part': item.role_or_part,
                'year_performed': item.year_performed,
                'notes': item.notes,
                'video_link': item.video_link,
                'is_featured': item.is_featured,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def delete_repertoire_item(request, item_id):
    """Удалить произведение из репертуара"""
    item = get_object_or_404(RepertoireItem, id=item_id)
    
    # Проверка прав доступа
    if request.user != item.performer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    item.delete()
    return JsonResponse({'success': True})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_repertoire_item(request, item_id):
    """Обновить произведение в репертуаре"""
    item = get_object_or_404(RepertoireItem, id=item_id)
    
    # Проверка прав доступа
    if request.user != item.performer.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        item.composer = data.get('composer', item.composer)
        item.work_title = data.get('work_title', item.work_title)
        item.category = data.get('category', item.category)
        item.epoch = data.get('epoch', item.epoch)
        item.role_or_part = data.get('role_or_part', item.role_or_part)
        item.year_performed = data.get('year_performed') or None
        item.notes = data.get('notes', item.notes)
        item.video_link = data.get('video_link', item.video_link)
        item.is_featured = data.get('is_featured', item.is_featured)
        
        item.save()
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'composer': item.composer,
                'work_title': item.work_title,
                'category': item.get_category_display(),
                'category_code': item.category,
                'epoch': item.get_epoch_display() if item.epoch else '',
                'role_or_part': item.role_or_part,
                'year_performed': item.year_performed,
                'notes': item.notes,
                'video_link': item.video_link,
                'is_featured': item.is_featured,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def reorder_repertoire(request):
    """Изменить порядок произведений (drag-and-drop)"""
    if not hasattr(request.user, 'performer_profile'):
        return JsonResponse({'error': 'Not a performer'}, status=403)
    
    try:
        data = json.loads(request.body)
        item_orders = data.get('items', [])  # [{id: 1, order: 0}, {id: 2, order: 1}, ...]
        
        for item_data in item_orders:
            item = RepertoireItem.objects.filter(
                id=item_data['id'],
                performer=request.user.performer_profile
            ).first()
            if item:
                item.order = item_data['order']
                item.save(update_fields=['order'])
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============= AUTOCOMPLETE APIs =============

@require_http_methods(["GET"])
def autocomplete_composers(request):
    """API для автодополнения композиторов"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'composers': []})
    
    # Ищем уникальных композиторов из уже введенных данных
    composers = RepertoireItem.objects.filter(
        composer__icontains=query
    ).values_list('composer', flat=True).distinct()[:10]
    
    return JsonResponse({'composers': list(composers)})


@require_http_methods(["GET"])
def autocomplete_works(request):
    """API для автодополнения произведений"""
    query = request.GET.get('q', '').strip()
    composer = request.GET.get('composer', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'works': []})
    
    # Фильтруем по композитору если указан
    filters = Q(work_title__icontains=query)
    if composer:
        filters &= Q(composer__icontains=composer)
    
    works = RepertoireItem.objects.filter(filters).values(
        'work_title', 'composer', 'category', 'role_or_part'
    ).distinct()[:10]
    
    return JsonResponse({'works': list(works)})
