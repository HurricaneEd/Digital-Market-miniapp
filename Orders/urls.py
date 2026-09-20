from rest_framework.routers import DefaultRouter

from .views import (
    AddressViewSet,
    AdminOrderViewSet,
    CartViewSet,
    OrderViewSet,
)


router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'addresses', AddressViewSet, basename='addresses')
router.register(r'admin/orders', AdminOrderViewSet, basename='admin-orders')

urlpatterns = router.urls
