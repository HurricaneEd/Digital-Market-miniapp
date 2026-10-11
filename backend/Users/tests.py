import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from Orders.models import Order

from .models import User


class UserNormalizationTests(TestCase):
    def test_optional_values_are_normalized_before_save(self):
        user = User.objects.create_user(
            username='normalized-user',
            password='password',
            phone='',
            email='  USER@EXAMPLE.COM  ',
            avatar=None,
            nickname=None,
        )

        self.assertIsNone(user.phone)
        self.assertEqual(user.email, 'user@example.com')
        self.assertEqual(user.avatar, '')
        self.assertEqual(user.nickname, '')


class UserDeletionIntegrityTests(APITestCase):
    def test_user_with_order_is_preserved(self):
        admin = User.objects.create_superuser(
            username='admin',
            password='password',
            email='admin@example.com',
        )
        buyer = User.objects.create_user(username='protected-buyer', password='password')
        Order.objects.create(
            order_sn='ORD-PROTECTED-USER',
            user=buyer,
            total_price=Decimal('10.00'),
        )
        self.client.force_authenticate(admin)

        response = self.client.delete(
            reverse('admin-users-detail', kwargs={'pk': buyer.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(User.objects.filter(pk=buyer.pk).exists())
        self.assertTrue(Order.objects.filter(user=buyer).exists())


class AvatarUploadApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='avatar-user',
            password='password',
        )
        self.client.force_authenticate(self.user)

    def test_authenticated_user_can_upload_avatar(self):
        avatar = SimpleUploadedFile(
            'avatar.png',
            b'\x89PNG\r\n\x1a\n' + b'test-avatar-content',
            content_type='image/png',
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse('users-upload-avatar'),
                    {'avatar': avatar},
                    format='multipart',
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.user.refresh_from_db()
                self.assertEqual(response.data['avatar'], self.user.avatar)
                relative_path = self.user.avatar.removeprefix('/media/')
                self.assertTrue(Path(media_root, relative_path).is_file())

    def test_avatar_upload_rejects_non_image_content(self):
        invalid_avatar = SimpleUploadedFile(
            'avatar.png',
            b'not-an-image',
            content_type='image/png',
        )

        response = self.client.post(
            reverse('users-upload-avatar'),
            {'avatar': invalid_avatar},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar, '')


class ProfileUpdateApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profile-user',
            password='old-password',
            email='old@example.com',
            phone='13800138000',
        )
        self.client.force_authenticate(self.user)

    def test_user_can_update_username_email_and_phone(self):
        response = self.client.put(
            reverse('users-profile'),
            {
                'username': 'updated-user',
                'email': '  UPDATED@EXAMPLE.COM  ',
                'phone': '13900139000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'updated-user')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.phone, '13900139000')
        self.assertEqual(response.data['username'], 'updated-user')

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username='existing-user', password='password')

        response = self.client.put(
            reverse('users-profile'),
            {'username': 'existing-user'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['username'][0], '用户名已存在')
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'profile-user')

    def test_user_can_change_password_after_old_password_is_verified(self):
        invalid_response = self.client.post(
            reverse('users-change-password'),
            {
                'old_password': 'wrong-password',
                'new_password': 'new-password',
                'confirm_password': 'new-password',
            },
            format='json',
        )
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            reverse('users-change-password'),
            {
                'old_password': 'old-password',
                'new_password': 'new-password',
                'confirm_password': 'new-password',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-password'))
