from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performers', '0006_repertoireitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='performerprofile',
            name='instrument',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='performerprofile',
            name='performer_type',
            field=models.CharField(choices=[('vocalist', 'Вокалист'), ('instrumentalist', 'Инструменталист')], default='vocalist', help_text='Основная специализация исполнителя', max_length=20),
        ),
    ]

