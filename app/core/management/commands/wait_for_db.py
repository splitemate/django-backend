"""
Django commands to wait for database to be available
"""
import time
from typing import Any
from django.core.management.base import BaseCommand

from psycopg2 import OperationalError as Psycopg2OpError
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Django commad to wait for database"""

    def handle(self, *args: Any, **options: Any) -> str | None:
        """Entrypoint for command"""
        self.stdout.write('Waiting for database')
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up = True
            except (Psycopg2OpError, OperationalError):
                self.stdout.write('Database Unavailable, waiting...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database available!"))
