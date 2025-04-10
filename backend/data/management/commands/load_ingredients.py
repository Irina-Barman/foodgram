import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str,
                            help='Path to the JSON file with ingredient data')

    def handle(self, *args, **kwargs):
        json_file_path = kwargs['json_file']
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:

                data = json.load(file)
                for item in data:
                    name = item.get('name')
                    measurement_unit = item.get('measurement_unit')

                    if not Ingredient.objects.filter(name=name).exists():
                        Ingredient.objects.create(
                            name=name,
                            measurement_unit=measurement_unit
                        )
                        self.stdout.write(self.style.WARNING(
                            f'Ingredient "{name}" is added successfully.'))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'Ingredient "{name}" already exists.'))

                self.stdout.write(self.style.SUCCESS(
                    'Successfully loaded ingredients.'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('JSON file not found.'))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('Error decoding JSON file.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
