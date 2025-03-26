from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_pdf(shopping_cart_items):
    ingredients_dict = {}

    for item in shopping_cart_items:
        recipe = item.recipe
        for recipe_ingredients in recipe.recipe_ingredients.all():
            ingredient = recipe_ingredients.ingredient
            amount = recipe_ingredients.amount

            if ingredient.name in ingredients_dict:
                ingredients_dict[ingredient.name] += amount
            else:
                ingredients_dict[ingredient.name] = amount

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="shopping_cart.pdf"'
    )

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica", 12)

    p.drawString(100, height - 50, "Список покупок")

    y_position = height - 80

    for ingredient_name, total_amount in ingredients_dict.items():
        p.drawString(100, y_position, f"{ingredient_name}: {total_amount}")
        y_position -= 20

    p.showPage()
    p.save()

    return response
