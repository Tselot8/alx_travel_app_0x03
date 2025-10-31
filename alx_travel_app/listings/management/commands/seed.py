from django.core.management.base import BaseCommand
from listings.models import Listing
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Seed the database with sample listings'

    def handle(self, *args, **kwargs):
        fake = Faker()
        self.stdout.write('Seeding database...')
        for _ in range(10):
            Listing.objects.create(
                name=fake.company(),
                description=fake.text(max_nb_chars=200),
                price_per_night=random.randint(50, 500),
                location=fake.city()
            )
        self.stdout.write(self.style.SUCCESS('Database seeding completed!'))
