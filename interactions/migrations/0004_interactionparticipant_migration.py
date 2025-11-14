from django.db import migrations, models
from django.conf import settings


def forward_copy_participants(apps, schema_editor):
    Interaction = apps.get_model('interactions', 'Interaction')
    Participant = apps.get_model('interactions', 'InteractionParticipant')
    AgentProfile = apps.get_model('agents', 'AgentProfile')
    ClientProfile = apps.get_model('clients', 'ClientProfile')
    PerformerProfile = apps.get_model('performers', 'PerformerProfile')

    for interaction in Interaction.objects.all():
        inviter_id = interaction.created_by_id
        # Agents
        try:
            agents = interaction.agents.all()
        except AttributeError:
            agents = []
        for agent in agents:
            if agent.user_id:
                Participant.objects.get_or_create(
                    interaction_id=interaction.id,
                    user_id=agent.user_id,
                    defaults={
                        'role': 'agent',
                        'status': 'accepted',
                        'invited_by_id': inviter_id,
                    }
                )
        # Venues
        try:
            venues = interaction.venues.all()
        except AttributeError:
            venues = []
        for venue in venues:
            if venue.user_id:
                Participant.objects.get_or_create(
                    interaction_id=interaction.id,
                    user_id=venue.user_id,
                    defaults={
                        'role': 'venue',
                        'status': 'accepted',
                        'invited_by_id': inviter_id,
                    }
                )
        # Performers
        try:
            performers = interaction.performers.all()
        except AttributeError:
            performers = []
        for performer in performers:
            if performer.user_id:
                Participant.objects.get_or_create(
                    interaction_id=interaction.id,
                    user_id=performer.user_id,
                    defaults={
                        'role': 'performer',
                        'status': 'accepted',
                        'invited_by_id': inviter_id,
                    }
                )

        # Normalise statuses that no longer exist
        if interaction.status in ('in_discussion', 'agreement'):
            interaction.status = 'proposal_sent'
            interaction.save(update_fields=['status'])


def reverse_copy_participants(apps, schema_editor):
    # No reverse transformation
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0001_initial'),
        ('clients', '0001_initial'),
        ('performers', '0006_repertoireitem'),
        ('interactions', '0003_alter_interaction_options_remove_interaction_agent_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InteractionParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('agent', 'Организатор'), ('venue', 'Площадка'), ('performer', 'Исполнитель')], max_length=20, verbose_name='Роль')),
                ('status', models.CharField(choices=[('pending', 'Ожидание ответа'), ('accepted', 'Принято'), ('declined', 'Отказано')], default='pending', max_length=20, verbose_name='Статус участия')),
                ('invited_at', models.DateTimeField(auto_now_add=True, verbose_name='Приглашён')),
                ('responded_at', models.DateTimeField(blank=True, null=True, verbose_name='Ответил')),
                ('interaction', models.ForeignKey(on_delete=models.CASCADE, related_name='participant_links', to='interactions.interaction', verbose_name='Проект')),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='project_invites', to=settings.AUTH_USER_MODEL, verbose_name='Кем приглашён')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='project_participations', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Участник проекта',
                'verbose_name_plural': 'Участники проекта',
                'unique_together': {('interaction', 'user', 'role')},
            },
        ),
        migrations.AlterField(
            model_name='interaction',
            name='status',
            field=models.CharField(choices=[('draft', 'Черновик'), ('proposal_sent', 'Предложение отправлено'), ('in_progress', 'В работе'), ('completed', 'Завершено'), ('cancelled', 'Отменено')], default='draft', max_length=32, verbose_name='Статус'),
        ),
        migrations.RunPython(forward_copy_participants, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(model_name='interaction', name='agents'),
        migrations.RemoveField(model_name='interaction', name='performers'),
        migrations.RemoveField(model_name='interaction', name='venues'),
    ]
