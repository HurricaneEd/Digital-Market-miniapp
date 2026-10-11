from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# 配置 API 文档基本信息
schema_view = get_schema_view(
   openapi.Info(
      title="项目 API",
      default_version='v1',
      description="API 接口文档描述",
      terms_of_service="https://www.example.com/terms/",
      contact=openapi.Contact(email="contact@example.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),  # 允许任何人访问文档
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # 各应用负责自己的 ViewSet 注册和 action 路由。
    path('api/', include('Users.urls')),
    path('api/', include('Product.urls')),
    path('api/', include('Orders.urls')),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
