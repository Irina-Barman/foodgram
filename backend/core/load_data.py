import csv
import os

import django
from recipes.models import Ingredient

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram_project.settings")
django.setup()

with open("/app/data/ingredients.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        ingredient = Ingredient(
            name=row["name"], measurement_unit=row["measurement_unit"]
        )
        ingredient.save()
