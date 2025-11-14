from django import forms

from agents.models import AgentProfile
from clients.models import ClientProfile
from performers.models import PerformerProfile
from .models import Interaction, InteractionParticipant, ProjectReport


class InteractionForm(forms.ModelForm):
    agents = forms.ModelMultipleChoiceField(
        queryset=AgentProfile.objects.none(),
        required=False,
        label='Организаторы',
    )
    venues = forms.ModelMultipleChoiceField(
        queryset=ClientProfile.objects.none(),
        required=False,
        label='Площадки',
    )
    performers = forms.ModelMultipleChoiceField(
        queryset=PerformerProfile.objects.none(),
        required=False,
        label='Исполнители',
    )
    interaction_type = forms.TypedChoiceField(
        choices=Interaction.TYPE_CHOICES,
        coerce=str,
        empty_value=None,
        label=Interaction._meta.get_field('interaction_type').verbose_name,
    )
    status = forms.TypedChoiceField(
        choices=Interaction.STATUS_CHOICES,
        coerce=str,
        empty_value=None,
        label=Interaction._meta.get_field('status').verbose_name,
    )

    class Meta:
        model = Interaction
        fields = [
            'title',
            'description',
            'interaction_type',
            'status',
            'start_date',
            'end_date',
            'budget_amount',
            'budget_currency',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.request_user = user
        super().__init__(*args, **kwargs)

        self.fields['title'].required = True
        self.fields['description'].required = True

        # Styling and defaults for standard fields
        for name, field in self.fields.items():
            css_class = 'form-control'
            if isinstance(field.widget, forms.SelectMultiple):
                css_class = 'form-select'
            elif isinstance(field.widget, forms.Select):
                css_class = 'form-select'
            elif getattr(field.widget, 'input_type', '') == 'checkbox':
                css_class = 'form-check-input'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing} {css_class}".strip()

        # Configure participant fields
        self.fields['agents'].queryset = AgentProfile.objects.select_related('user').only('id', 'display_name', 'user')
        self.fields['venues'].queryset = ClientProfile.objects.select_related('user').only('id', 'company_name', 'user')
        self.fields['performers'].queryset = PerformerProfile.objects.select_related('user').only(
            'id',
            'full_name',
            'user',
            'voice_type',
            'instrument',
            'performer_type',
        )

        self.fields['agents'].label = 'Организаторы'
        self.fields['venues'].label = 'Площадки'
        self.fields['performers'].label = 'Исполнители'

        self.fields['agents'].widget.attrs.update({
            'class': 'form-select participant-select-control',
            'data-participant': 'agents',
        })
        self.fields['venues'].widget.attrs.update({
            'class': 'form-select participant-select-control',
            'data-participant': 'venues',
        })
        self.fields['performers'].widget.attrs.update({
            'class': 'form-select participant-select-control',
            'data-participant': 'performers',
        })

        self.fields['agents'].label_from_instance = lambda obj: obj.display_name
        self.fields['venues'].label_from_instance = lambda obj: obj.company_name
        def performer_label(obj):
            if hasattr(obj, 'performer_type') and obj.performer_type == PerformerProfile.PERFORMER_TYPE_INSTRUMENTALIST:
                if getattr(obj, 'instrument', ''):
                    return f"{obj.full_name} — {obj.instrument}"
            if getattr(obj, 'voice_type', ''):
                return f"{obj.full_name} — {obj.voice_type}"
            return obj.full_name

        self.fields['performers'].label_from_instance = performer_label

        self.fields['agents'].required = False
        self.fields['venues'].required = False
        self.fields['performers'].required = False

        # Initial selections
        if self.instance.pk:
            participant_links = self.instance.participant_links.select_related('user')
            self.fields['agents'].initial = [link.profile.pk for link in participant_links if link.role == InteractionParticipant.ROLE_AGENT and link.profile]
            self.fields['venues'].initial = [link.profile.pk for link in participant_links if link.role == InteractionParticipant.ROLE_VENUE and link.profile]
            self.fields['performers'].initial = [link.profile.pk for link in participant_links if link.role == InteractionParticipant.ROLE_PERFORMER and link.profile]
        else:
            if self.request_user and hasattr(self.request_user, 'agent_profile'):
                self.fields['agents'].initial = [self.request_user.agent_profile.pk]
            if self.request_user and hasattr(self.request_user, 'client_profile'):
                self.fields['venues'].initial = [self.request_user.client_profile.pk]
            if self.request_user and hasattr(self.request_user, 'performer_profile'):
                self.fields['performers'].initial = [self.request_user.performer_profile.pk]

        # Default status for new projects
        if not self.is_bound and not self.instance.pk:
            self.fields['status'].initial = Interaction.STATUS_DRAFT

        # Reorder fields for wizard steps
        self.order_fields([
            'title',
            'description',
            'interaction_type',
            'status',
            'agents',
            'venues',
            'performers',
            'start_date',
            'end_date',
            'budget_amount',
            'budget_currency',
        ])

    def clean(self):
        cleaned = super().clean()

        def ensure_self_profile(field_key, current_user_attr):
            participants = cleaned.get(field_key)
            if participants is None:
                participants = self.fields[field_key].queryset.none()
            if self.request_user and hasattr(self.request_user, current_user_attr):
                profile = getattr(self.request_user, current_user_attr)
                if profile:
                    participants = participants | self.fields[field_key].queryset.filter(pk=profile.pk)
            cleaned[field_key] = participants.distinct()

        ensure_self_profile('agents', 'agent_profile')
        ensure_self_profile('venues', 'client_profile')
        ensure_self_profile('performers', 'performer_profile')

        return cleaned

    # Custom save / participants sync -----------------------------------------
    def save(self, commit=True, created_by=None):
        interaction = super().save(commit=False)
        is_new = interaction.pk is None
        if is_new and created_by is not None:
            interaction.created_by = created_by
        if commit:
            interaction.save()
        self._sync_participants(interaction)
        interaction.update_status_from_participants()
        return interaction

    def _sync_participants(self, interaction: Interaction):
        if not interaction.pk:
            return

        role_map = {
            InteractionParticipant.ROLE_AGENT: self.cleaned_data.get('agents') or AgentProfile.objects.none(),
            InteractionParticipant.ROLE_VENUE: self.cleaned_data.get('venues') or ClientProfile.objects.none(),
            InteractionParticipant.ROLE_PERFORMER: self.cleaned_data.get('performers') or PerformerProfile.objects.none(),
        }

        for role, profiles in role_map.items():
            existing_links = {
                link.user_id: link
                for link in interaction.participant_links.filter(role=role)
            }

            new_user_ids = set()
            for profile in profiles:
                user = getattr(profile, 'user', None)
                if not user:
                    continue
                new_user_ids.add(user.id)
                if user.id in existing_links:
                    continue

                status = InteractionParticipant.STATUS_PENDING
                if interaction.can_manage(self.request_user) and user == self.request_user:
                    status = InteractionParticipant.STATUS_ACCEPTED

                interaction.add_participant(
                    user=user,
                    role=role,
                    invited_by=self.request_user,
                    status=status,
                )

            # Remove users that were unselected
            to_remove = set(existing_links.keys()) - new_user_ids
            for user_id in to_remove:
                interaction.participant_links.filter(role=role, user_id=user_id).delete()


class ProjectReportForm(forms.ModelForm):
    class Meta:
        model = ProjectReport
        fields = ['summary', 'highlights', 'audience', 'feedback', 'media_link', 'attachment']
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'feedback': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ('summary', 'feedback'):
                continue
            field.widget.attrs['class'] = 'form-control'

