from django.db import migrations, models


def assign_roles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    ClientProfile = apps.get_model('clients', 'ClientProfile')
    PerformerProfile = apps.get_model('performers', 'PerformerProfile')

    performer_user_ids = set(
        PerformerProfile.objects.values_list('user_id', flat=True)
    )
    client_user_ids = set(
        ClientProfile.objects.values_list('user_id', flat=True)
    )

    for user in User.objects.all():
        if user.id in performer_user_ids:
            user.role = 'performer'
        elif user.id in client_user_ids:
            user.role = 'client'
        else:
            # Leave as default 'performer' for now; can be adjusted manually later
            user.role = user.role or 'performer'
        user.save(update_fields=['role'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('clients', '0001_initial'),
        ('performers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('performer', 'Исполнитель'), ('client', 'Площадка'), ('agent', 'Организатор')], default='performer', max_length=20),
        ),
        migrations.RunPython(assign_roles, migrations.RunPython.noop),
    ]

