from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

from Product.views import ProductViewSet, AdminProductViewSet, SmartRecommendView, CategoryViewSet, BrandViewSet, ReviewViewSet
from Product import views as product_views
from Product.stats_views import dashboard_stats, dashboard_detail, dashboard_heatmap
from Users.views import UserViewSet, UserActionViewSet, FavoriteViewSet, AdminUserViewSet
from Orders.views import CartViewSet, OrderViewSet, AdminOrderViewSet, AddressViewSet
from Recomm.views import (
    UnifiedRecommendView,
    HeatRecommendationView,
    ProductHeatDetailView
)

# 1. 创建路由器并注册 ViewSet
router = routers.DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'addresses', AddressViewSet, basename='addresses')
router.register(r'admin/products', AdminProductViewSet, basename='admin-products')
router.register(r'admin/orders', AdminOrderViewSet, basename='admin-orders')
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'users', UserViewSet, basename='users')
router.register(r'actions', UserActionViewSet, basename='actions')
router.register(r'favorites', FavoriteViewSet, basename='favorites')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'brands', BrandViewSet, basename='brands')
router.register(r'reviews', ReviewViewSet, basename='reviews')

# 打印所有注册的路由以便调试
print("注册的路由:")
for route in router.registry:
    print(f"  {route[0]} -> {route[1]}")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/users/login/', UserViewSet.as_view({'post': 'login'}), name='user-login'),
    path('api/users/register/', UserViewSet.as_view({'post': 'register'}), name='user-register'),
    path('api/smart-recommend/', product_views.SmartRecommendView.as_view(), name='smart_recommend'),
    # 用户相关
    path('api/users/profile/', UserViewSet.as_view({'get': 'profile', 'put': 'profile'}), name='user-profile'),
    path('api/users/change_password/', UserViewSet.as_view({'post': 'change_password'}), name='user-change-password'),
    path('api/users/upload_avatar/', UserViewSet.as_view({'post': 'upload_avatar'}), name='user-upload-avatar'),
    # 推荐算法接口
    path('api/recommend/', UnifiedRecommendView.as_view(), name='recommend'),  # 统一接口
    path('api/recommend/hot/', HeatRecommendationView.as_view(), name='recommend-hot'),
    path('api/recommend/heat/detail/', ProductHeatDetailView.as_view(), name='recommend-heat-detail'),
    # 数据统计
    path('api/dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('api/dashboard/detail/<str:chart_type>/', dashboard_detail, name='dashboard-detail'),
    path('api/dashboard/heatmap/', dashboard_heatmap, name='dashboard-heatmap'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
