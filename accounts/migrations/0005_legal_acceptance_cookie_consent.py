from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_display_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='CookieConsent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('policy_version', models.CharField(max_length=40)),
                ('accepted_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cookie_consents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-accepted_at'],
            },
        ),
        migrations.CreateModel(
            name='LegalAcceptance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_slug', models.CharField(max_length=80)),
                ('document_title', models.CharField(max_length=255)),
                ('document_version', models.CharField(max_length=40)),
                ('accepted_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='legal_acceptances', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-accepted_at'],
                'unique_together': {('user', 'document_slug', 'document_version')},
            },
        ),
        migrations.AddIndex(
            model_name='cookieconsent',
            index=models.Index(fields=['user', 'policy_version'], name='accounts_co_user_id_7a0dde_idx'),
        ),
        migrations.AddIndex(
            model_name='legalacceptance',
            index=models.Index(fields=['user', 'document_slug', 'document_version'], name='accounts_le_user_id_558330_idx'),
        ),
    ]
