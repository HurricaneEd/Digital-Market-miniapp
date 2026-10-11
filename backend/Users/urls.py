from rest_framework.routers import DefaultRouter

from .views import AdminUserViewSet, UserViewSet


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')

urlpatterns = router.urls
