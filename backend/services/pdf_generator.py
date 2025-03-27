from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def generate_pdf(shopping_cart_items):
    ingredients_dict = {}

    if not shopping_cart_items:
        return HttpResponse("Ваша корзина пуста.", content_type="text/plain")

    for item in shopping_cart_items:
        recipe = item.recipe
        for recipe_ingredients in recipe.recipe_ingredients.all():
            ingredient = recipe_ingredients.ingredient
            amount = recipe_ingredients.amount

            if ingredient.name in ingredients_dict:
                ingredients_dict[ingredient.name]["amount"] += amount
            else:
                ingredients_dict[ingredient.name] = {
                    "amount": amount,
                    "unit": ingredient.measurement_unit,
                }

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="shopping_cart.pdf"'
    )

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Регистрация шрифта Arial
    pdfmetrics.registerFont(TTFont("Arial", "/app/services/Arial.ttf"))
    p.setFont("Arial", 12)  # Установка шрифта Arial

    p.drawString(100, height - 50, "Список покупок")

    y_position = height - 80

    for ingredient_name, details, total_amount in ingredients_dict.items():
        total_amount = details["amount"]
        unit = details["unit"]
        p.drawString(
            100, y_position, f"{ingredient_name}: {total_amount} {unit}"
        )
        y_position -= 20

    p.showPage()
    p.save()

    return response
