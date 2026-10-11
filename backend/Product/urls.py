from rest_framework.routers import DefaultRouter

from .views import (
    AdminProductViewSet,
    BrandViewSet,
    CategoryViewSet,
    ProductViewSet,
    ReviewViewSet,
)


router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'admin/products', AdminProductViewSet, basename='admin-products')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'brands', BrandViewSet, basename='brands')
router.register(r'reviews', ReviewViewSet, basename='reviews')

urlpatterns = router.urls
