"""
Django signals for users app
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserPreference
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Create user preferences when a new user is created"""
    if created and not instance.preferences:
        preferences = UserPreference.objects.create()
        instance.preferences = preferences
        instance.save(update_fields=['preferences'])
        
        logger.info(
            f"Created preferences for user: {instance.email}",
            extra={'user_id': str(instance.id)}
        )
