from django.conf import settings
from django.db import models
from django.utils import timezone

from agents.models import AgentProfile
from clients.models import ClientProfile
from performers.models import PerformerProfile


class Interaction(models.Model):
    TYPE_ONE_TIME = 'one_time'
    TYPE_LONG_TERM = 'long_term'
    TYPE_CHOICES = [
        (TYPE_ONE_TIME, 'Разовое сотрудничество'),
        (TYPE_LONG_TERM, 'Долгосрочное сотрудничество'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_PROPOSAL_SENT = 'proposal_sent'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PROPOSAL_SENT, 'Предложение отправлено'),
        (STATUS_IN_PROGRESS, 'В работе'),
        (STATUS_COMPLETED, 'Завершено'),
        (STATUS_CANCELLED, 'Отменено'),
    ]

    CURRENCY_RUB = 'RUB'
    CURRENCY_USD = 'USD'
    CURRENCY_EUR = 'EUR'
    CURRENCY_CHOICES = [
        (CURRENCY_RUB, '₽'),
        (CURRENCY_USD, '$'),
        (CURRENCY_EUR, '€'),
    ]

    title = models.CharField('Название', max_length=255)
    description = models.TextField('Описание')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Создано пользователем',
        on_delete=models.CASCADE,
        related_name='created_interactions',
    )
    interaction_type = models.CharField(
        'Тип проекта',
        max_length=32,
        choices=TYPE_CHOICES,
    )
    status = models.CharField(
        'Статус',
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    start_date = models.DateField('Дата начала', null=True, blank=True)
    end_date = models.DateField('Дата окончания', null=True, blank=True)
    budget_amount = models.DecimalField(
        'Бюджет',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    budget_currency = models.CharField(
        'Валюта бюджета',
        max_length=3,
        choices=CURRENCY_CHOICES,
        default=CURRENCY_RUB,
    )
    success_flag = models.BooleanField('Успешно завершено', default=False)
    result_notes = models.TextField('Результаты', blank=True)
    completion_requested_at = models.DateTimeField('Запрос завершения', null=True, blank=True)
    completion_completed_at = models.DateTimeField('Дата завершения', null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    # --- Participants helpers -------------------------------------------------

    def participants(self):
        return self.participant_links.select_related('user')

    def participants_by_role(self, role, statuses=None):
        qs = self.participant_links.filter(role=role).select_related('user')
        if statuses is not None:
            if isinstance(statuses, (list, tuple, set)):
                qs = qs.filter(status__in=statuses)
            else:
                qs = qs.filter(status=statuses)
        return qs

    def accepted_participants_by_role(self, role):
        return self.participants_by_role(
            role, statuses=InteractionParticipant.STATUS_ACCEPTED
        )

    def get_participant(self, user):
        try:
            return self.participant_links.get(user=user)
        except InteractionParticipant.DoesNotExist:
            return None

    def add_participant(self, *, user, role, invited_by=None, status=None):
        if status is None:
            status = InteractionParticipant.STATUS_PENDING
        participant, created = InteractionParticipant.objects.update_or_create(
            interaction=self,
            user=user,
            role=role,
            defaults={
                'status': status,
                'invited_by': invited_by or self.created_by,
                'responded_at': timezone.now() if status != InteractionParticipant.STATUS_PENDING else None,
            }
        )
        if created:
            participant.invited_at = timezone.now()
            participant.save(update_fields=['invited_at'])
        return participant

    def remove_participant(self, user):
        self.participant_links.filter(user=user).delete()

    def update_status_from_participants(self):
        participants = self.participant_links.all()
        if not participants.exists():
            self.status = self.STATUS_DRAFT
            self.save(update_fields=['status'])
            return

        pending_exists = participants.filter(status=InteractionParticipant.STATUS_PENDING).exists()
        accepted_exists = participants.filter(status=InteractionParticipant.STATUS_ACCEPTED).exists()

        if pending_exists:
            self.status = self.STATUS_PROPOSAL_SENT
        else:
            if self.status not in (self.STATUS_COMPLETED, self.STATUS_CANCELLED):
                self.status = self.STATUS_IN_PROGRESS if accepted_exists else self.STATUS_PROPOSAL_SENT
        self.save(update_fields=['status'])

        if self.status in (self.STATUS_DRAFT, self.STATUS_PROPOSAL_SENT):
            self.reset_completion_workflow()

    def reset_completion_workflow(self):
        self.completion_requested_at = None
        if self.status != self.STATUS_COMPLETED:
            self.completion_completed_at = None
        self.save(update_fields=['completion_requested_at', 'completion_completed_at'])
        self.participant_links.update(
            completion_status=InteractionParticipant.COMPLETION_NOT_REQUESTED,
            completion_requested_at=None,
            completion_responded_at=None,
        )

    def can_request_completion(self):
        if self.status != self.STATUS_IN_PROGRESS:
            return False
        accepted_participants = self.participant_links.filter(status=InteractionParticipant.STATUS_ACCEPTED)
        return accepted_participants.exists()

    def start_completion_confirmation(self):
        if not self.can_request_completion():
            return False

        now = timezone.now()
        self.completion_requested_at = now
        self.save(update_fields=['completion_requested_at'])

        accepted_participants = self.participant_links.filter(status=InteractionParticipant.STATUS_ACCEPTED)
        for link in accepted_participants:
            if link.user_id == self.created_by_id or getattr(link.user, 'is_superuser', False):
                link.mark_completion_confirmed()
                if not link.completion_requested_at:
                    link.completion_requested_at = now
                    link.save(update_fields=['completion_requested_at'])
            else:
                link.completion_status = InteractionParticipant.COMPLETION_PENDING
                link.completion_requested_at = now
                link.completion_responded_at = None
                link.save(update_fields=['completion_status', 'completion_requested_at', 'completion_responded_at'])

        return True

    def is_completion_confirmation_active(self):
        accepted_participants = self.participant_links.filter(status=InteractionParticipant.STATUS_ACCEPTED)
        return accepted_participants.filter(
            completion_status__in=[
                InteractionParticipant.COMPLETION_PENDING,
                InteractionParticipant.COMPLETION_DECLINED,
            ]
        ).exists()

    def evaluate_completion_confirmation(self):
        accepted_participants = self.participant_links.filter(status=InteractionParticipant.STATUS_ACCEPTED)
        if not accepted_participants.exists():
            return

        if accepted_participants.filter(completion_status=InteractionParticipant.COMPLETION_DECLINED).exists():
            # At least one participant declined completion, keep project active
            self.status = self.STATUS_IN_PROGRESS
            self.save(update_fields=['status'])
            return

        outstanding = accepted_participants.filter(
            completion_status__in=[
                InteractionParticipant.COMPLETION_NOT_REQUESTED,
                InteractionParticipant.COMPLETION_PENDING,
            ]
        )
        if outstanding.exists():
            return

        self.status = self.STATUS_COMPLETED
        self.success_flag = True
        self.completion_completed_at = timezone.now()
        self.save(update_fields=['status', 'success_flag', 'completion_completed_at'])

    def cancel_project(self):
        self.status = self.STATUS_CANCELLED
        self.reset_completion_workflow()
        self.save(update_fields=['status', 'completion_requested_at', 'completion_completed_at'])

    def is_creator(self, user):
        return bool(user) and user == self.created_by

    def can_manage(self, user):
        return bool(user) and (getattr(user, 'is_superuser', False) or self.is_creator(user))

    def user_participation_status(self, user):
        if self.can_manage(user):
            return InteractionParticipant.STATUS_ACCEPTED
        participant = self.get_participant(user)
        return participant.status if participant else None

    def agents_queryset(self):
        return self.accepted_participants_by_role(InteractionParticipant.ROLE_AGENT)

    def venues_queryset(self):
        return self.accepted_participants_by_role(InteractionParticipant.ROLE_VENUE)

    def performers_queryset(self):
        return self.accepted_participants_by_role(InteractionParticipant.ROLE_PERFORMER)


class InteractionParticipant(models.Model):
    ROLE_AGENT = 'agent'
    ROLE_VENUE = 'venue'
    ROLE_PERFORMER = 'performer'
    ROLE_CHOICES = [
        (ROLE_AGENT, 'Организатор'),
        (ROLE_VENUE, 'Площадка'),
        (ROLE_PERFORMER, 'Исполнитель'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидание ответа'),
        (STATUS_ACCEPTED, 'Принято'),
        (STATUS_DECLINED, 'Отказано'),
    ]

    COMPLETION_NOT_REQUESTED = 'not_requested'
    COMPLETION_PENDING = 'pending'
    COMPLETION_CONFIRMED = 'confirmed'
    COMPLETION_DECLINED = 'declined'
    COMPLETION_STATUS_CHOICES = [
        (COMPLETION_NOT_REQUESTED, 'Не запрошено'),
        (COMPLETION_PENDING, 'Ожидает подтверждения'),
        (COMPLETION_CONFIRMED, 'Подтверждено'),
        (COMPLETION_DECLINED, 'Отклонено'),
    ]

    interaction = models.ForeignKey(
        Interaction,
        on_delete=models.CASCADE,
        related_name='participant_links',
        verbose_name='Проект',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_participations',
        verbose_name='Пользователь',
    )
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES)
    status = models.CharField('Статус участия', max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='project_invites',
        verbose_name='Кем приглашён',
        null=True,
        blank=True,
    )
    invited_at = models.DateTimeField('Приглашён', auto_now_add=True)
    responded_at = models.DateTimeField('Ответил', null=True, blank=True)
    completion_status = models.CharField(
        'Статус подтверждения завершения',
        max_length=20,
        choices=COMPLETION_STATUS_CHOICES,
        default=COMPLETION_NOT_REQUESTED,
    )
    completion_requested_at = models.DateTimeField('Запрос подтверждения', null=True, blank=True)
    completion_responded_at = models.DateTimeField('Ответ на подтверждение', null=True, blank=True)

    class Meta:
        unique_together = ('interaction', 'user', 'role')
        verbose_name = 'Участник проекта'
        verbose_name_plural = 'Участники проекта'

    def __str__(self):
        return f"{self.user} — {self.get_role_display()} ({self.get_status_display()})"

    # Convenience accessors ----------------------------------------------------
    @property
    def profile(self):
        if self.role == self.ROLE_AGENT and hasattr(self.user, 'agent_profile'):
            return self.user.agent_profile
        if self.role == self.ROLE_VENUE and hasattr(self.user, 'client_profile'):
            return self.user.client_profile
        if self.role == self.ROLE_PERFORMER and hasattr(self.user, 'performer_profile'):
            return self.user.performer_profile
        return None

    @property
    def display_name(self):
        profile = self.profile
        if isinstance(profile, AgentProfile):
            return profile.display_name
        if isinstance(profile, ClientProfile):
            return profile.company_name
        if isinstance(profile, PerformerProfile):
            specialization = profile.specialization_display
            if specialization:
                return f"{profile.full_name} — {specialization}"
            return profile.full_name
        return self.user.get_full_name() or self.user.username

    def mark_accepted(self):
        now = timezone.now()
        self.status = self.STATUS_ACCEPTED
        self.responded_at = now
        self.completion_status = self.COMPLETION_NOT_REQUESTED
        self.completion_requested_at = None
        self.completion_responded_at = None
        self.save(update_fields=[
            'status',
            'responded_at',
            'completion_status',
            'completion_requested_at',
            'completion_responded_at',
        ])

    def mark_declined(self):
        now = timezone.now()
        self.status = self.STATUS_DECLINED
        self.responded_at = now
        self.completion_status = self.COMPLETION_NOT_REQUESTED
        self.completion_requested_at = None
        self.completion_responded_at = None
        self.save(update_fields=[
            'status',
            'responded_at',
            'completion_status',
            'completion_requested_at',
            'completion_responded_at',
        ])

    def mark_completion_pending(self):
        now = timezone.now()
        self.completion_status = self.COMPLETION_PENDING
        self.completion_requested_at = now
        self.completion_responded_at = None
        self.save(update_fields=['completion_status', 'completion_requested_at', 'completion_responded_at'])

    def mark_completion_confirmed(self):
        now = timezone.now()
        self.completion_status = self.COMPLETION_CONFIRMED
        if not self.completion_requested_at:
            self.completion_requested_at = now
        self.completion_responded_at = now
        self.save(update_fields=['completion_status', 'completion_requested_at', 'completion_responded_at'])

    def mark_completion_declined(self):
        now = timezone.now()
        self.completion_status = self.COMPLETION_DECLINED
        if not self.completion_requested_at:
            self.completion_requested_at = now
        self.completion_responded_at = now
        self.save(update_fields=['completion_status', 'completion_requested_at', 'completion_responded_at'])


class InteractionEvent(models.Model):
    EVENT_NOTE = 'note'
    EVENT_STATUS_CHANGE = 'status_change'
    EVENT_FILE = 'file'
    EVENT_MILESTONE = 'milestone'
    EVENT_CHOICES = [
        (EVENT_NOTE, 'Комментарий'),
        (EVENT_STATUS_CHANGE, 'Изменение статуса'),
        (EVENT_FILE, 'Файл'),
        (EVENT_MILESTONE, 'Этап'),
    ]

    interaction = models.ForeignKey(
        Interaction,
        verbose_name='Взаимодействие',
        on_delete=models.CASCADE,
        related_name='events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор события',
        on_delete=models.CASCADE,
        related_name='interaction_events',
    )
    event_type = models.CharField(
        'Тип события',
        max_length=32,
        choices=EVENT_CHOICES,
        default=EVENT_NOTE,
    )
    text = models.TextField('Описание', blank=True)
    attachment = models.FileField(
        'Файл',
        upload_to='interactions/attachments/',
        blank=True,
        null=True,
    )
    metadata = models.JSONField('Дополнительные данные', blank=True, null=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Событие взаимодействия'
        verbose_name_plural = 'События взаимодействий'

    def __str__(self):
        return f"{self.get_event_type_display()} для {self.interaction}"


class ProjectReport(models.Model):
    interaction = models.ForeignKey(
        Interaction,
        verbose_name='Проект',
        on_delete=models.CASCADE,
        related_name='reports',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор отчёта',
        on_delete=models.CASCADE,
        related_name='project_reports',
    )
    summary = models.TextField('Резюме проекта')
    highlights = models.JSONField('Ключевые моменты', blank=True, null=True)
    audience = models.CharField('Аудитория / заказчик', max_length=255, blank=True)
    feedback = models.TextField('Отзывы', blank=True)
    media_link = models.URLField('Ссылка на материалы', blank=True)
    attachment = models.FileField(
        'Файл отчёта',
        upload_to='interactions/reports/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Отчёт по проекту'
        verbose_name_plural = 'Отчёты по проектам'

    def __str__(self):
        return f"Отчёт по {self.interaction.title} от {self.author}"

# Create your models here.
