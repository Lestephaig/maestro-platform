from django import template

register = template.Library()


@register.filter
def participants_by_role(interaction, role):
    """
    Template filter that returns the queryset of participants for a given role.
    Usage: {{ interaction|participants_by_role:'agent' }}
    """
    if hasattr(interaction, 'participants_by_role'):
        return interaction.participants_by_role(role)
    return []


@register.filter
def user_participation(interaction, user):
    if hasattr(interaction, 'get_participant'):
        return interaction.get_participant(user)
    return None

