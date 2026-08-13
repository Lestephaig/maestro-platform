from django.db import migrations


def copy_existing_full_names(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    PerformerProfile = apps.get_model('performers', 'PerformerProfile')
    AgentProfile = apps.get_model('agents', 'AgentProfile')
    ClientProfile = apps.get_model('clients', 'ClientProfile')

    performer_names = dict(PerformerProfile.objects.values_list('user_id', 'full_name'))
    agent_names = dict(AgentProfile.objects.values_list('user_id', 'display_name'))
    client_names = dict(ClientProfile.objects.values_list('user_id', 'contact_person'))

    users_to_update = []
    for user in User.objects.all().iterator():
        if user.role == 'performer':
            current_full_name = performer_names.get(user.id, '')
        elif user.role == 'agent':
            current_full_name = agent_names.get(user.id, '')
        elif user.role == 'client':
            current_full_name = client_names.get(user.id, '')
        else:
            current_full_name = ''

        current_full_name = (
            current_full_name
            or user.display_name
            or f'{user.first_name} {user.last_name}'.strip()
        ).strip()
        if not current_full_name:
            continue

        user.first_name = current_full_name
        user.last_name = ''
        users_to_update.append(user)

    User.objects.bulk_update(users_to_update, ['first_name', 'last_name'])


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_alter_user_first_name'),
        ('performers', '0011_musicinstrument_performerprofile_city_and_more'),
        ('agents', '0002_agentprofile_city_agentprofile_country'),
        ('clients', '0004_clientprofile_city_clientprofile_country'),
    ]

    operations = [
        migrations.RunPython(copy_existing_full_names, migrations.RunPython.noop),
    ]
