"""
Management command to run RabbitMQ consumer
"""

from django.core.management.base import BaseCommand

from users.rabbitmq_consumer import run_consumer


class Command(BaseCommand):
    """Django management command to run RabbitMQ consumer"""

    help = "Run RabbitMQ consumer for push notifications"

    def handle(self, *args, **options):
        """Execute the command"""
        self.stdout.write(self.style.SUCCESS("Starting RabbitMQ consumer..."))
        run_consumer()
