from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="chat/index.html"), name="home"),
    path("healthz/", include("chat.health_urls")),
    path("api/", include("chat.urls")),
]
