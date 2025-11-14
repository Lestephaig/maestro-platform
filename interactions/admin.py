from django.contrib import admin

from .models import Interaction, InteractionEvent, InteractionParticipant, ProjectReport


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'interaction_type',
        'status',
        'agents_list',
        'venues_list',
        'performers_list',
        'start_date',
        'end_date',
        'created_at',
    )
    list_filter = ('interaction_type', 'status', 'success_flag', 'created_at')
    search_fields = ('title', 'description', 'participant_links__user__username')
    autocomplete_fields = ('created_by',)
    date_hierarchy = 'created_at'

    @admin.display(description='Организаторы')
    def agents_list(self, obj):
        return ', '.join(link.display_name for link in obj.accepted_participants_by_role(InteractionParticipant.ROLE_AGENT)) or '—'

    @admin.display(description='Площадки')
    def venues_list(self, obj):
        return ', '.join(link.display_name for link in obj.accepted_participants_by_role(InteractionParticipant.ROLE_VENUE)) or '—'

    @admin.display(description='Исполнители')
    def performers_list(self, obj):
        return ', '.join(link.display_name for link in obj.accepted_participants_by_role(InteractionParticipant.ROLE_PERFORMER)) or '—'


@admin.register(InteractionEvent)
class InteractionEventAdmin(admin.ModelAdmin):
    list_display = ('interaction', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('interaction__title', 'text', 'actor__username')
    autocomplete_fields = ('interaction', 'actor')


@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ('interaction', 'author', 'created_at')
    search_fields = ('interaction__title', 'summary', 'author__username')
    autocomplete_fields = ('interaction', 'author')
    date_hierarchy = 'created_at'

# Register your models here.
