from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Brand, Category, Product, Review
from .serializer import CategorySerializer, ProductSerializer, ReviewSerializer


User = get_user_model()


class ReviewContractTests(SimpleTestCase):
    def test_analysis_fields_are_not_part_of_review_model_or_api(self):
        removed_fields = {'clean_content', 'sentiment_score', 'sentiment_label'}
        model_fields = {field.name for field in Review._meta.get_fields()}
        serializer_fields = set(ReviewSerializer().fields)

        self.assertTrue(removed_fields.isdisjoint(model_fields))
        self.assertTrue(removed_fields.isdisjoint(serializer_fields))


class ReviewApiTests(APITestCase):
    def test_review_can_still_be_created_and_queried(self):
        brand = Brand.objects.create(name='评论测试品牌')
        category = Category.objects.create(code='review', name='评论测试分类')
        product = Product.objects.create(
            prod_id='P-REVIEW',
            brand=brand,
            category=category,
            name='评论测试商品',
            price=Decimal('10.00'),
        )

        create_response = self.client.post(
            reverse('reviews-list'),
            {
                'product': product.pk,
                'author_name': '访客',
                'content': '评论接口仍然可用',
                'rating': 4.5,
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        detail_response = self.client.get(
            reverse('reviews-detail', kwargs={'id': create_response.data['id']}),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['content'], '评论接口仍然可用')
        self.assertNotIn('clean_content', detail_response.data)
        self.assertNotIn('sentiment_score', detail_response.data)
        self.assertNotIn('sentiment_label', detail_response.data)


class CategoryIntegrityTests(TestCase):
    def test_category_cycle_is_rejected_by_model_and_serializer(self):
        root = Category.objects.create(code='root', name='根分类')
        child = Category.objects.create(code='child', name='子分类', parent=root)

        serializer = CategorySerializer(root, data={'parent': child.pk}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('parent', serializer.errors)

        root.parent = child
        with self.assertRaises(ValidationError):
            root.save()


class ProductRatingTests(TestCase):
    def test_missing_rating_is_not_included_in_average(self):
        brand = Brand.objects.create(name='测试品牌')
        category = Category.objects.create(code='rating', name='评分分类')
        product = Product.objects.create(
            prod_id='P-RATING',
            brand=brand,
            category=category,
            name='评分商品',
            price=Decimal('10.00'),
        )
        Review.objects.create(product=product, content='无评分', rating=None)
        rated_review = Review.objects.create(
            product=product,
            content='有评分',
            rating=Decimal('4.5'),
        )

        self.assertEqual(ProductSerializer(product).data['rate'], 4.5)
        self.assertEqual(ReviewSerializer(rated_review).data['rating'], Decimal('4.5'))


class ProductOriginTests(APITestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='产地测试品牌')
        self.category = Category.objects.create(code='origin', name='产地测试分类')
        self.admin = User.objects.create_superuser(
            username='origin-admin',
            password='test-password',
            email='origin-admin@example.com',
        )

    def test_existing_product_defaults_to_blank_origin_and_public_api_returns_it(self):
        product = Product.objects.create(
            prod_id='P-ORIGIN-OLD',
            brand=self.brand,
            category=self.category,
            name='旧商品',
            price=Decimal('99.00'),
        )

        self.assertEqual(product.origin, '')
        response = self.client.get(
            reverse('products-detail', kwargs={'prod_id': product.prod_id}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('origin', response.data)
        self.assertEqual(response.data['origin'], '')

    def test_admin_can_create_and_update_origin_and_overlength_is_rejected(self):
        self.client.force_authenticate(self.admin)
        create_response = self.client.post(
            reverse('admin-products-list'),
            {
                'brand': self.brand.pk,
                'category': self.category.pk,
                'name': '带产地商品',
                'origin': '中国广东',
                'price': '199.00',
                'stock': 8,
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['origin'], '中国广东')
        product = Product.objects.get(prod_id=create_response.data['prod_id'])
        self.assertEqual(product.origin, '中国广东')

        detail_url = reverse('admin-products-detail', kwargs={'prod_id': product.prod_id})
        update_response = self.client.patch(
            detail_url,
            {'origin': '中国江苏'},
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['origin'], '中国江苏')
        product.refresh_from_db()
        self.assertEqual(product.origin, '中国江苏')

        invalid_response = self.client.patch(
            detail_url,
            {'origin': '产' * 101},
            format='json',
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('origin', invalid_response.data)
        product.refresh_from_db()
        self.assertEqual(product.origin, '中国江苏')


class ProductVisibilityTests(APITestCase):
    def test_public_api_hides_inactive_product_but_admin_api_can_retrieve_it(self):
        brand = Brand.objects.create(name='上下架测试品牌')
        category = Category.objects.create(code='visibility', name='上下架测试分类')
        active_product = Product.objects.create(
            prod_id='P-ACTIVE',
            brand=brand,
            category=category,
            name='在售商品',
            price=Decimal('10.00'),
            is_active=True,
        )
        inactive_product = Product.objects.create(
            prod_id='P-INACTIVE',
            brand=brand,
            category=category,
            name='下架商品',
            price=Decimal('10.00'),
            is_active=False,
        )

        list_response = self.client.get(reverse('products-list'))
        product_ids = [item['prod_id'] for item in list_response.data['results']]
        self.assertIn(active_product.prod_id, product_ids)
        self.assertNotIn(inactive_product.prod_id, product_ids)

        public_detail = self.client.get(
            reverse('products-detail', kwargs={'prod_id': inactive_product.prod_id}),
        )
        self.assertEqual(public_detail.status_code, status.HTTP_404_NOT_FOUND)

        admin = User.objects.create_superuser(
            username='visibility-admin',
            password='test-password',
            email='visibility-admin@example.com',
        )
        self.client.force_authenticate(admin)
        admin_detail = self.client.get(
            reverse('admin-products-detail', kwargs={'prod_id': inactive_product.prod_id}),
        )
        self.assertEqual(admin_detail.status_code, status.HTTP_200_OK)
