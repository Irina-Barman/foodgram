from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def generate_pdf(ingredients):
    if not ingredients:
        return HttpResponse("Ваша корзина пуста.", content_type="text/plain")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="shopping_cart.pdf"'
    )

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Регистрация шрифта Arial
    pdfmetrics.registerFont(TTFont("Arial", "/app/services/Arial.ttf"))
    p.setFont("Arial", 12)

    p.drawString(100, height - 50, "Список покупок")

    y_position = height - 80

    for ingredient in ingredients:
        ingredient_name = ingredient["name"]
        total_amount = ingredient["amount"]
        unit = ingredient["unit"]

        p.drawString(
            100, y_position, f"{ingredient_name}: {total_amount} {unit}"
        )
        y_position -= 20

    p.showPage()
    p.save()

    return response
