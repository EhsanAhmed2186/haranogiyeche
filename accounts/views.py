from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .access import get_membership, has_community_access
from .forms import (
    AvatarForm,
    CommunityForm,
    JoinCommunityForm,
    RegistrationForm,
)
from .models import Community, Membership, User


def _safe_next(request):
    """The page to return to after registering, but only if it is on this site."""
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return ""


# ---------- public pages (guests allowed) ----------

def home(request):
    """Guests see a welcome page. Logged-in users see their own communities."""
    if request.user.is_authenticated:
        if request.user.is_superadmin:
            return redirect("accounts:superadmin_dashboard")
        memberships = (
            Membership.objects.filter(user=request.user)
            .select_related("community")
            .order_by("community__name")
        )
        return render(request, "home.html", {"memberships": memberships})

    featured = Community.objects.annotate(member_count=Count("memberships")).order_by(
        "-member_count", "name"
    )[:6]
    return render(request, "landing.html", {"featured": featured})


def community_list(request):
    """
    Public list of communities: name and member count only. Join codes, admins,
    members and posts are never shown here. Joining still needs an account AND the code.
    """
    query = request.GET.get("q", "").strip()
    communities = Community.objects.annotate(member_count=Count("memberships"))
    if query:
        communities = communities.filter(name__icontains=query)

    my_ids = set()
    if request.user.is_authenticated:
        my_ids = set(request.user.memberships.values_list("community_id", flat=True))
        if request.user.is_superadmin:
            my_ids.update(Community.objects.values_list("pk", flat=True))

    items = list(communities)
    for community in items:
        community.is_member = community.pk in my_ids

    return render(request, "accounts/community_list.html", {"communities": items, "query": query})


def about(request):
    return render(request, "accounts/about.html")


# ---------- accounts ----------

def register(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(next_url or "home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to Haranogiyeche! Your account has been created.")
            return redirect(next_url or "home")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form, "next": next_url})


def _delete_stored_file(field_file):
    if field_file and field_file.name:
        field_file.storage.delete(field_file.name)


@login_required
def profile(request):
    """Your own profile. You can only ever change your own photo."""
    user = request.user
    # Remember the current photo first: validating the form swaps in the new one.
    old_name = user.avatar.name if user.avatar else ""
    form = AvatarForm(instance=user)

    if request.method == "POST":
        if "remove_avatar" in request.POST:
            _delete_stored_file(user.avatar)
            user.avatar = None
            user.save(update_fields=["avatar"])
            messages.success(request, "Your profile photo was removed.")
            return redirect("profile")

        form = AvatarForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save()
            if old_name and old_name != user.avatar.name:
                user.avatar.storage.delete(old_name)  # do not keep unused old photos
            messages.success(request, "Your profile photo was updated.")
            return redirect("profile")

    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("community")
        .order_by("community__name")
    )
    context = {
        "form": form,
        "memberships": memberships,
        "post_count": request.user.posts.count(),
    }
    return render(request, "accounts/profile.html", context)


# ---------- communities (logged-in users) ----------

@login_required
def create_community(request):
    """The logged-in user becomes the admin (never taken from the form)."""
    if request.method == "POST":
        form = CommunityForm(request.POST)
        if form.is_valid():
            community = form.save(commit=False)
            community.admin = request.user
            community.save()  # Community.save() also creates the admin Membership
            messages.success(request, f"Community “{community.name}” created.")
            return redirect("newsfeed:feed", community_id=community.pk)
    else:
        form = CommunityForm()

    return render(request, "accounts/community_form.html", {"form": form})


@login_required
def join_community(request):
    """Join with a code. A wrong code or a repeat join never creates anything bad."""
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
                return redirect("newsfeed:feed", community_id=community.pk)
    else:
        form = JoinCommunityForm()

    return render(request, "accounts/join_community.html", {"form": form})


@login_required
def community_detail(request, pk):
    """Community members directory; community entry itself opens the feed."""
    community = get_object_or_404(Community, pk=pk)
    membership = get_membership(request.user, community)
    if not has_community_access(request.user, community):
        raise PermissionDenied  # shows Django's 403 page

    members = community.memberships.select_related("user").order_by("user__username")
    context = {
        "community": community,
        "membership": membership,
        "is_admin": request.user.is_superadmin or community.admin_id == request.user.id,
        "is_superadmin": request.user.is_superadmin,
        "members": members,
    }
    return render(request, "accounts/community_detail.html", context)


@login_required
def manage_membership(request, pk, membership_id):
    if request.method != "POST":
        raise PermissionDenied
    community = get_object_or_404(Community, pk=pk)
    actor_membership = get_membership(request.user, community)
    is_admin = request.user.is_superadmin or community.admin_id == request.user.id or (
        actor_membership and actor_membership.role == Membership.Role.ADMIN
    )
    if not is_admin:
        raise PermissionDenied

    target = get_object_or_404(Membership, pk=membership_id, community=community)
    action = request.POST.get("action")
    if action == "remove":
        if target.user_id == community.admin_id and not request.user.is_superadmin:
            raise PermissionDenied
        if target.user_id == request.user.id and not request.user.is_superadmin:
            raise PermissionDenied
        target.delete()
        messages.success(request, f"{target.user.username} was removed from {community.name}.")
    elif action == "promote" and target.role == Membership.Role.MEMBER:
        target.role = Membership.Role.MODERATOR
        target.save(update_fields=["role"])
        messages.success(request, f"{target.user.username} is now a moderator.")
    elif action == "demote" and target.role == Membership.Role.MODERATOR:
        target.role = Membership.Role.MEMBER
        target.save(update_fields=["role"])
        messages.success(request, f"{target.user.username} is now a member.")
    else:
        messages.error(request, "That membership action is not available.")
    return redirect("accounts:community_detail", pk=community.pk)


@login_required
def superadmin_dashboard(request):
    if not request.user.is_superadmin:
        raise PermissionDenied
    if request.method == "POST":
        target = get_object_or_404(User, pk=request.POST.get("user_id"))
        if target.pk == request.user.pk or target.is_superuser:
            messages.error(request, "You cannot change your own superadmin role here.")
        else:
            target.role = (
                User.Role.MEMBER if target.is_superadmin else User.Role.SUPERADMIN
            )
            target.save(update_fields=["role"])
            messages.success(request, f"Updated {target.username}'s platform role.")
        return redirect("accounts:superadmin_dashboard")
    return render(request, "accounts/superadmin_dashboard.html", {
        "users": User.objects.order_by("username"),
        "communities": Community.objects.annotate(member_count=Count("memberships")),
        "community_count": Community.objects.count(),
        "user_count": User.objects.count(),
    })
