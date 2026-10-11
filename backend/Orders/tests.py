from decimal import Decimal

from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from Product.models import Brand, Category, Product
from Users.models import User

from .models import Address, CartItem, Order


class OrderIntegrityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer',
            password='test-password',
            phone='13800138000',
            email='buyer@example.com',
        )
        brand = Brand.objects.create(name='测试品牌')
        category = Category.objects.create(code='test-category', name='测试分类')
        self.product = Product.objects.create(
            prod_id='P-TEST-1',
            brand=brand,
            category=category,
            name='测试商品',
            price=Decimal('19.90'),
            stock=5,
        )
        self.address = Address.objects.create(
            user=self.user,
            receiver='测试用户',
            phone='13800138000',
            detail='测试地址',
            is_default=True,
        )
        self.client.force_authenticate(self.user)

    def create_order(self, count=2):
        cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            count=count,
        )
        return self.client.post(
            reverse('orders-list'),
            {'address_id': self.address.pk, 'cart_item_ids': [cart_item.pk]},
            format='json',
        )

    def test_create_order_deducts_stock_and_removes_cart_item(self):
        response = self.create_order(count=2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())
        order = Order.objects.get(order_sn=response.data['order_sn'])
        self.assertEqual(order.total_price, Decimal('39.80'))
        self.assertEqual(order.items.get().product_name, self.product.name)

    def test_insufficient_stock_does_not_create_partial_order(self):
        response = self.create_order(count=6)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_buy_now_creates_order_without_changing_cart(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            count=1,
        )

        response = self.client.post(
            reverse('orders-list'),
            {
                'address_id': self.address.pk,
                'product_id': self.product.prod_id,
                'count': 2,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertTrue(CartItem.objects.filter(pk=cart_item.pk).exists())
        order = Order.objects.get(order_sn=response.data['order_sn'])
        self.assertEqual(order.total_price, Decimal('39.80'))
        self.assertEqual(order.items.get().count, 2)

    def test_buy_now_rejects_insufficient_stock_atomically(self):
        response = self.client.post(
            reverse('orders-list'),
            {
                'address_id': self.address.pk,
                'product_id': self.product.prod_id,
                'count': 6,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_rejects_mixed_checkout_sources(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            count=1,
        )

        response = self.client.post(
            reverse('orders-list'),
            {
                'address_id': self.address.pk,
                'cart_item_ids': [cart_item.pk],
                'product_id': self.product.prod_id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_cancel_restores_stock_only_once(self):
        create_response = self.create_order(count=2)
        cancel_url = reverse(
            'orders-cancel',
            kwargs={'order_sn': create_response.data['order_sn']},
        )

        first_response = self.client.post(cancel_url)
        second_response = self.client.post(cancel_url)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_user_cannot_patch_order_core_fields(self):
        create_response = self.create_order(count=1)
        detail_url = reverse(
            'orders-detail',
            kwargs={'order_sn': create_response.data['order_sn']},
        )

        response = self.client.patch(
            detail_url,
            {'total_price': '0.00', 'status': Order.Status.COMPLETED},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_paid_order_requires_payment_method_at_database_level(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Order.objects.create(
                    order_sn='ORD-CONSTRAINT-TEST',
                    user=self.user,
                    total_price=Decimal('10.00'),
                    status=Order.Status.PAID,
                    payment_method=None,
                )

    def test_order_payment_and_confirm_receive_actions(self):
        create_response = self.create_order(count=1)
        order_sn = create_response.data['order_sn']
        pay_response = self.client.post(
            reverse('orders-pay', kwargs={'order_sn': order_sn}),
            {'payment_method': Order.PaymentMethod.WECHAT},
            format='json',
        )
        self.assertEqual(pay_response.status_code, status.HTTP_200_OK)

        order = Order.objects.get(order_sn=order_sn)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.payment_method, Order.PaymentMethod.WECHAT)

        confirm_url = reverse(
            'orders-confirm-receive',
            kwargs={'order_sn': order_sn},
        )
        early_confirm_response = self.client.post(confirm_url)
        self.assertEqual(
            early_confirm_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        Order.objects.filter(pk=order.pk).update(status=Order.Status.SHIPPED)
        confirm_response = self.client.post(confirm_url)
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)


class AddressIntegrityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='address-user', password='password')
        self.client.force_authenticate(self.user)

    def test_first_address_is_default_and_new_default_replaces_it(self):
        url = reverse('addresses-list')
        first = self.client.post(
            url,
            {'receiver': '甲', 'phone': '13800138000', 'detail': '地址一'},
            format='json',
        )
        second = self.client.post(
            url,
            {
                'receiver': '乙',
                'phone': '13900139000',
                'detail': '地址二',
                'is_default': True,
            },
            format='json',
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)
        self.assertEqual(
            Address.objects.get(user=self.user, is_default=True).receiver,
            '乙',
        )


class CartApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cart-user', password='password')
        brand = Brand.objects.create(name='购物车测试品牌')
        category = Category.objects.create(code='cart-category', name='购物车测试分类')
        self.product = Product.objects.create(
            prod_id='P-CART-1',
            brand=brand,
            category=category,
            name='购物车测试商品',
            price=Decimal('29.90'),
            stock=10,
        )
        self.client.force_authenticate(self.user)

    def test_cart_create_list_patch_and_delete(self):
        list_url = reverse('cart-list')
        create_response = self.client.post(
            list_url,
            {'product_id': self.product.prod_id, 'count': 2, 'selected': True},
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        cart_item_id = create_response.data['id']
        self.assertEqual(create_response.data['count'], 2)

        duplicate_response = self.client.post(
            list_url,
            {'product_id': self.product.prod_id, 'count': 1, 'selected': True},
            format='json',
        )
        self.assertEqual(duplicate_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicate_response.data['id'], cart_item_id)
        self.assertEqual(duplicate_response.data['count'], 3)

        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(
            list_response.data['results'][0]['product']['prod_id'],
            self.product.prod_id,
        )

        detail_url = reverse('cart-detail', kwargs={'pk': cart_item_id})
        patch_response = self.client.patch(
            detail_url,
            {'count': 4, 'selected': False},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['count'], 4)
        self.assertFalse(patch_response.data['selected'])

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(pk=cart_item_id).exists())

    def test_cart_count_cannot_exceed_current_stock(self):
        list_url = reverse('cart-list')
        overstock_response = self.client.post(
            list_url,
            {'product_id': self.product.prod_id, 'count': 11},
            format='json',
        )
        self.assertEqual(overstock_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

        create_response = self.client.post(
            list_url,
            {'product_id': self.product.prod_id, 'count': 8},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['product']['stock'], 10)
        self.assertTrue(create_response.data['product']['is_active'])

        duplicate_response = self.client.post(
            list_url,
            {'product_id': self.product.prod_id, 'count': 3},
            format='json',
        )
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

        cart_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.count, 8)
        detail_url = reverse('cart-detail', kwargs={'pk': cart_item.pk})
        patch_response = self.client.patch(detail_url, {'count': 11}, format='json')
        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.count, 8)
