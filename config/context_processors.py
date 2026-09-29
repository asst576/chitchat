from django.conf import settings


def app_mount(request):
    return {"app_base_path": settings.APP_BASE_PATH}
