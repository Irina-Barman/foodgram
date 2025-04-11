from urllib.parse import urljoin

from django.shortcuts import redirect
from rest_framework.generics import get_object_or_404

from recipes.models import ShortRecipeURL


def redirect_to_original(request, short_code):
    url = get_object_or_404(ShortRecipeURL, short_code=short_code)
    domain = request.get_host()

    target_url = urljoin(f"http://{domain}/", f"recipes/{url.recipe.id}")

    return redirect(target_url)
