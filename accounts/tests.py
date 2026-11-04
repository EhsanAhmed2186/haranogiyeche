import os
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Community, Membership

User = get_user_model()
STRONG_PASSWORD = "Str0ng-Pass-9271!"


class PublicPagesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", "admin1@example.com")
        self.member = User.objects.create_user("member", "member@example.com")
        self.outsider = User.objects.create_user("outsider", "outsider@example.com")
        self.community = Community.objects.create(name="Test Uni", admin=self.admin)
        Membership.objects.create(user=self.member, community=self.community)

    def test_guest_sees_landing_page_with_theme_toggle(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Explore communities")
        self.assertContains(response, 'id="themeToggle"')
        self.assertNotContains(response, "My Communities")

    def test_logged_in_user_sees_own_communities_on_home(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "My Communities")
        self.assertContains(response, "Test Uni")

    def test_guest_can_list_communities_without_private_data(self):
        response = self.client.get(reverse("community_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Uni")
        self.assertNotContains(response, self.community.join_code)
        self.assertNotContains(response, "admin1")

    def test_guest_must_register_to_join(self):
        response = self.client.get(reverse("community_list"))
        self.assertContains(response, "Register to join")
        self.assertContains(response, reverse("accounts:join_community"))

    def test_search_filters_communities(self):
        Community.objects.create(name="Other Club", admin=self.admin)
        response = self.client.get(reverse("community_list"), {"q": "Test"})
        self.assertContains(response, "Test Uni")
        self.assertNotContains(response, "Other Club")

    def test_member_sees_open_and_outsider_sees_join_with_code(self):
        feed_url = reverse("newsfeed:feed", args=[self.community.pk])

        self.client.force_login(self.member)
        self.assertContains(self.client.get(reverse("community_list")), feed_url)

        self.client.force_login(self.outsider)
        response = self.client.get(reverse("community_list"))
        self.assertContains(response, "Join with code")
        self.assertNotContains(response, feed_url)

    def test_about_page_is_public(self):
        self.assertEqual(self.client.get(reverse("about")).status_code, 200)

    def test_community_page_is_still_members_only(self):
        url = reverse("accounts:community_detail", args=[self.community.pk])
        self.assertEqual(self.client.get(url).status_code, 302)  # guest -> login
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 403)


class CommunityManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("community_admin", "admin@example.com", STRONG_PASSWORD)
        self.member = User.objects.create_user("community_member", "member@example.com", STRONG_PASSWORD)
        self.outsider = User.objects.create_user("outsider2", "outsider2@example.com", STRONG_PASSWORD)
        self.community = Community.objects.create(name="Managed Campus", admin=self.admin)
        self.membership = Membership.objects.create(user=self.member, community=self.community)
        self.url = reverse(
            "accounts:manage_membership", args=[self.community.pk, self.membership.pk]
        )

    def test_community_admin_can_promote_demote_and_remove_a_member(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {"action": "promote"})
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, Membership.Role.MODERATOR)

        self.client.post(self.url, {"action": "demote"})
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, Membership.Role.MEMBER)

        self.client.post(self.url, {"action": "remove"})
        self.assertFalse(Membership.objects.filter(pk=self.membership.pk).exists())

    def test_regular_member_cannot_manage_members(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(self.url, {"action": "remove"}).status_code, 403)
        self.assertTrue(Membership.objects.filter(pk=self.membership.pk).exists())

    def test_superadmin_has_dashboard_and_community_access(self):
        superadmin = User.objects.create_user(
            "platform_admin", "platform@example.com", STRONG_PASSWORD,
            role=User.Role.SUPERADMIN,
        )
        self.client.force_login(superadmin)
        self.assertContains(self.client.get(reverse("accounts:superadmin_dashboard")), "Managed Campus")
        self.assertEqual(
            self.client.get(reverse("newsfeed:feed", args=[self.community.pk])).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("accounts:community_detail", args=[self.community.pk])).status_code,
            200,
        )


class ProfileTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", "admin1@example.com")
        self.member = User.objects.create_user("member", "member@example.com")
        self.community = Community.objects.create(name="Test Uni", admin=self.admin)
        Membership.objects.create(user=self.member, community=self.community)

    def test_guest_is_sent_to_login_and_returned_afterwards(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response.url)

    def test_profile_shows_own_data(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "member@example.com")
        self.assertContains(response, "Test Uni")
        self.assertNotContains(response, "admin1@example.com")


class RegisterNextTests(TestCase):
    def register(self, next_url):
        return self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
                "next": next_url,
            },
        )

    def test_register_returns_to_join_page(self):
        response = self.register(reverse("accounts:join_community"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:join_community"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_external_next_is_ignored(self):
        response = self.register("https://evil.example/")
        self.assertEqual(response.url, reverse("home"))


class RemovedPasswordResetTests(TestCase):
    def test_legacy_reset_url_returns_404(self):
        response = self.client.get("/accounts/password-reset/")
        self.assertEqual(response.status_code, 404)


def make_image(name="me.png", fmt="PNG", size=(24, 24)):
    buffer = BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/" + fmt.lower())


class AvatarTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = tempfile.mkdtemp()  # uploads go to a throw-away folder
        cls._override = override_settings(MEDIA_ROOT=cls.media_dir)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls.media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user("farhan", "farhan@example.com")
        self.client.force_login(self.user)
        self.url = reverse("profile")

    def file_exists(self, name):
        return os.path.exists(os.path.join(self.media_dir, name))

    def test_upload_saves_the_photo_in_the_users_own_folder(self):
        response = self.client.post(self.url, {"avatar": make_image()})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar.name.startswith(f"avatars/user_{self.user.pk}/"))
        self.assertTrue(self.user.avatar.name.endswith(".png"))
        self.assertNotIn("me", os.path.basename(self.user.avatar.name))  # visitor's file name not used
        self.assertTrue(self.file_exists(self.user.avatar.name))

    def test_photo_shows_on_the_profile_page_and_in_the_navbar(self):
        self.client.post(self.url, {"avatar": make_image()})
        self.user.refresh_from_db()
        for page in (reverse("profile"), reverse("about")):
            self.assertContains(self.client.get(page), self.user.avatar.url)

    def test_without_a_photo_the_initial_is_shown(self):
        response = self.client.get(reverse("about"))
        self.assertNotContains(response, "/media/avatars/")
        self.assertContains(response, "F")

    def test_a_file_that_is_not_an_image_is_rejected(self):
        fake = SimpleUploadedFile("evil.png", b"this is not an image", content_type="image/png")
        response = self.client.post(self.url, {"avatar": fake})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_an_unsupported_image_format_is_rejected(self):
        response = self.client.post(self.url, {"avatar": make_image("a.bmp", "BMP")})
        self.assertContains(response, "JPG, PNG, GIF or WEBP")
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_a_photo_over_2_mb_is_rejected(self):
        noise = Image.frombytes("RGB", (900, 900), os.urandom(900 * 900 * 3))
        buffer = BytesIO()
        noise.save(buffer, "PNG")
        self.assertGreater(len(buffer.getvalue()), 2 * 1024 * 1024)
        big = SimpleUploadedFile("big.png", buffer.getvalue(), content_type="image/png")
        response = self.client.post(self.url, {"avatar": big})
        self.assertContains(response, "2 MB or smaller")
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_replacing_the_photo_deletes_the_old_file(self):
        self.client.post(self.url, {"avatar": make_image()})
        self.user.refresh_from_db()
        old_name = self.user.avatar.name

        self.client.post(self.url, {"avatar": make_image("second.png")})
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.avatar.name, old_name)
        self.assertFalse(self.file_exists(old_name))
        self.assertTrue(self.file_exists(self.user.avatar.name))

    def test_remove_photo_clears_it_and_deletes_the_file(self):
        self.client.post(self.url, {"avatar": make_image()})
        self.user.refresh_from_db()
        name = self.user.avatar.name

        self.client.post(self.url, {"remove_avatar": "1"})
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)
        self.assertFalse(self.file_exists(name))

    def test_guest_cannot_upload(self):
        self.client.logout()
        response = self.client.post(self.url, {"avatar": make_image()})
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
