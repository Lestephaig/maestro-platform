from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InteractionForm, ProjectReportForm
from .models import Interaction, InteractionParticipant


def _accessible_interactions_queryset(user):
    qs = Interaction.objects.all().select_related('created_by').prefetch_related('participant_links__user')
    if user.is_superuser:
        return qs

    filters = Q(created_by=user) | Q(participant_links__user=user)
    return qs.filter(filters).distinct()


@login_required
def interaction_list(request):
    interactions_qs = _accessible_interactions_queryset(request.user).order_by('-created_at')
    interaction_entries = []
    for interaction in interactions_qs:
        interaction_entries.append({
            'interaction': interaction,
            'participants': {
                'agents': interaction.participants_by_role(InteractionParticipant.ROLE_AGENT),
                'venues': interaction.participants_by_role(InteractionParticipant.ROLE_VENUE),
                'performers': interaction.participants_by_role(InteractionParticipant.ROLE_PERFORMER),
            },
        })

    return render(request, 'interactions/interaction_list.html', {
        'project_entries': interaction_entries,
    })


@login_required
def interaction_detail(request, pk):
    interaction = get_object_or_404(_accessible_interactions_queryset(request.user), pk=pk)
    can_manage = interaction.can_manage(request.user)
    is_creator = interaction.is_creator(request.user)
    participant_record = interaction.get_participant(request.user)
    report_form = ProjectReportForm() if can_manage else None
    participant_groups = {
        InteractionParticipant.ROLE_AGENT: interaction.participants_by_role(InteractionParticipant.ROLE_AGENT),
        InteractionParticipant.ROLE_VENUE: interaction.participants_by_role(InteractionParticipant.ROLE_VENUE),
        InteractionParticipant.ROLE_PERFORMER: interaction.participants_by_role(InteractionParticipant.ROLE_PERFORMER),
    }
    completion_pending = interaction.participant_links.filter(
        status=InteractionParticipant.STATUS_ACCEPTED,
        completion_status=InteractionParticipant.COMPLETION_PENDING,
    ).select_related('user')
    completion_declined = interaction.participant_links.filter(
        status=InteractionParticipant.STATUS_ACCEPTED,
        completion_status=InteractionParticipant.COMPLETION_DECLINED,
    ).select_related('user')
    return render(request, 'interactions/interaction_detail.html', {
        'interaction': interaction,
        'report_form': report_form,
        'participant_record': participant_record,
        'can_manage': can_manage,
        'participant_groups': participant_groups,
        'is_creator': is_creator,
        'completion_requested_at': interaction.completion_requested_at,
        'completion_pending': completion_pending,
        'completion_declined': completion_declined,
        'completion_active': interaction.is_completion_confirmation_active(),
    })


@login_required
def interaction_create(request):
    form = InteractionForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        interaction = form.save(created_by=request.user)
        messages.success(request, 'Проект создан.')
        return redirect('interactions:detail', pk=interaction.pk)

    return render(request, 'interactions/interaction_form.html', {
        'form': form,
        'title': 'Новый проект',
    })


@login_required
def interaction_update(request, pk):
    interaction = get_object_or_404(_accessible_interactions_queryset(request.user), pk=pk)
    if not interaction.can_manage(request.user):
        messages.error(request, 'У вас нет прав на редактирование этого проекта.')
        return redirect('interactions:detail', pk=interaction.pk)
    form = InteractionForm(request.POST or None, instance=interaction, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Проект обновлён.')
        return redirect('interactions:detail', pk=interaction.pk)

    return render(request, 'interactions/interaction_form.html', {
        'form': form,
        'title': 'Редактирование проекта',
        'interaction': interaction,
    })


@login_required
def interaction_add_report(request, pk):
    interaction = get_object_or_404(_accessible_interactions_queryset(request.user), pk=pk)
    if not interaction.can_manage(request.user):
        messages.error(request, 'У вас нет прав на добавление отчётов в этот проект.')
        return redirect('interactions:detail', pk=interaction.pk)
    if request.method != 'POST':
        return redirect('interactions:detail', pk=interaction.pk)

    form = ProjectReportForm(request.POST, request.FILES)
    if form.is_valid():
        report = form.save(commit=False)
        report.interaction = interaction
        report.author = request.user
        report.save()
        messages.success(request, 'Отчёт сохранён.')
    else:
        messages.error(request, 'Не удалось сохранить отчёт. Проверьте форму.')

    return redirect('interactions:detail', pk=interaction.pk)


@login_required
def my_projects(request):
    if request.user.is_superuser:
        interactions = Interaction.objects.all().select_related('created_by').prefetch_related('participant_links__user').order_by('-created_at')
    else:
        interactions = Interaction.objects.filter(
            Q(created_by=request.user) | Q(participant_links__user=request.user)
        ).distinct().select_related('created_by').prefetch_related('participant_links__user').order_by('-created_at')

    projects = []
    participation_index = {
        link.interaction_id: link
        for link in InteractionParticipant.objects.filter(interaction__in=interactions, user=request.user)
    }

    for interaction in interactions:
        link = participation_index.get(interaction.id)
        is_creator = interaction.is_creator(request.user)
        if interaction.can_manage(request.user):
            participant_status = InteractionParticipant.STATUS_ACCEPTED
            participant_obj = None if is_creator else link
        else:
            participant_status = link.status if link else None
            participant_obj = link

        completion_status = participant_obj.completion_status if participant_obj else None
        completion_request = None
        completion_declined = False
        if participant_obj and participant_obj.status == InteractionParticipant.STATUS_ACCEPTED:
            if participant_obj.completion_status == InteractionParticipant.COMPLETION_PENDING:
                completion_request = participant_obj
            elif participant_obj.completion_status == InteractionParticipant.COMPLETION_DECLINED:
                completion_declined = True

        projects.append({
            'interaction': interaction,
            'participant_status': participant_status,
            'participant': participant_obj,
            'is_creator': is_creator,
            'completion_status': completion_status,
            'completion_request': completion_request,
            'completion_declined': completion_declined,
            'completion_active': interaction.is_completion_confirmation_active(),
        })

    return render(request, 'interactions/my_projects.html', {
        'projects': projects,
    })


@login_required
def participant_decision(request, pk, decision):
    participation = get_object_or_404(
        InteractionParticipant.objects.select_related('interaction'),
        pk=pk,
        user=request.user,
    )
    interaction = participation.interaction

    if decision == 'accept':
        participation.mark_accepted()
        messages.success(request, 'Вы приняли приглашение в проект.')
    elif decision == 'decline':
        participation.mark_declined()
        participation.delete()
        messages.info(request, 'Вы отказались от участия в проекте.')
    else:
        messages.error(request, 'Некорректное действие.')
        return redirect('interactions:my_projects')

    interaction.update_status_from_participants()
    return redirect('interactions:my_projects')


@login_required
def cancel_project(request, pk):
    interaction = get_object_or_404(_accessible_interactions_queryset(request.user), pk=pk)
    if not interaction.is_creator(request.user):
        return redirect('interactions:detail', pk=interaction.pk)
    if request.method == 'POST':
        interaction.cancel_project()
        interaction.participant_links.update(
            completion_status=InteractionParticipant.COMPLETION_NOT_REQUESTED,
            completion_requested_at=None,
            completion_responded_at=None,
        )
    return redirect('interactions:detail', pk=interaction.pk)


@login_required
def complete_project(request, pk):
    interaction = get_object_or_404(_accessible_interactions_queryset(request.user), pk=pk)
    if not interaction.is_creator(request.user):
        return redirect('interactions:detail', pk=interaction.pk)
    if request.method == 'POST':
        started = interaction.start_completion_confirmation()
        if started:
            interaction.evaluate_completion_confirmation()
    return redirect('interactions:detail', pk=interaction.pk)


@login_required
def participant_completion_decision(request, pk, decision):
    participation = get_object_or_404(
        InteractionParticipant.objects.select_related('interaction'),
        pk=pk,
        user=request.user,
    )
    interaction = participation.interaction
    if request.method != 'POST':
        return redirect('interactions:my_projects')

    if participation.status != InteractionParticipant.STATUS_ACCEPTED:
        return redirect('interactions:my_projects')

    if decision == 'confirm':
        participation.mark_completion_confirmed()
    elif decision == 'decline':
        participation.mark_completion_declined()
    else:
        return redirect('interactions:my_projects')

    interaction.evaluate_completion_confirmation()
    return redirect('interactions:my_projects')
