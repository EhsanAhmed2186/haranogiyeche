from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    # Django's LogoutView only accepts POST, so the navbar uses a small form.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("communities/create/", views.create_community, name="create_community"),
    path("communities/join/", views.join_community, name="join_community"),
    path("communities/<int:pk>/", views.community_detail, name="community_detail"),
]