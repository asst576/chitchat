from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView

from chat import views

urlpatterns = [
    path(
        "",
        login_required(
            TemplateView.as_view(
                template_name="chat/index.html",
                extra_context={"current_page": "chat"},
            )
        ),
        name="home",
    ),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/login/", views.AccountLoginView.as_view(), name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("billing/", views.billing, name="billing"),
    path("healthz/", include("chat.health_urls")),
    path("api/", include("chat.urls")),
]
