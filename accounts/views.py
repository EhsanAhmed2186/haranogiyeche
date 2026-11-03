from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .access import get_membership
from .forms import CommunityForm, JoinCommunityForm, RegistrationForm
from .models import Community, Membership


def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to Haranogiyeche! Your account has been created.")
            return redirect("home")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def home(request):
    """Step 5: My communities. Only communities the user belongs to are listed."""
    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("community")
        .order_by("community__name")
    )
    return render(request, "home.html", {"memberships": memberships})


@login_required
def create_community(request):
    """Step 6: the logged-in user becomes the admin (never taken from the form)."""
    if request.method == "POST":
        form = CommunityForm(request.POST)
        if form.is_valid():
            community = form.save(commit=False)
            community.admin = request.user
            community.save()  # Community.save() also creates the admin Membership
            messages.success(request, f"Community “{community.name}” created.")
            return redirect("accounts:community_detail", pk=community.pk)
    else:
        form = CommunityForm()

    return render(request, "accounts/community_form.html", {"form": form})


@login_required
def join_community(request):
    """Step 7: join with a code. A wrong code or a repeat join never creates anything bad."""
    if request.method == "POST":
        form = JoinCommunityForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["join_code"]
            community = Community.objects.filter(join_code=code).first()

            if community is None:
                form.add_error("join_code", "No community found with that code.")
            else:
                _, created = Membership.objects.get_or_create(
                    user=request.user,
                    community=community,
                    defaults={"role": Membership.Role.MEMBER},
                )
                if created:
                    messages.success(request, f"You joined “{community.name}”.")
                else:
                    messages.info(request, f"You are already a member of “{community.name}”.")
                return redirect("accounts:community_detail", pk=community.pk)
    else:
        form = JoinCommunityForm()

    return render(request, "accounts/join_community.html", {"form": form})


@login_required
def community_detail(request, pk):
    """Step 8 (needed as the target of the links above). Members only."""
    community = get_object_or_404(Community, pk=pk)
    membership = get_membership(request.user, community)
    if membership is None:
        raise PermissionDenied  # shows Django's 403 page

    members = community.memberships.select_related("user").order_by("user__username")
    context = {
        "community": community,
        "membership": membership,
        "is_admin": membership.role == Membership.Role.ADMIN,
        "members": members,
    }
    return render(request, "accounts/community_detail.html", context)