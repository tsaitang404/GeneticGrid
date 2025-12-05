from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('market/', views.market_view, name='market'),
    path('api/candlesticks/', views.api_candlesticks, name='api_candlesticks'),
    path('api/ticker/', views.api_ticker, name='api_ticker'),
    path('api/proxy-status/', views.api_proxy_status, name='api_proxy_status'),
    
    # 插件系统 API 端点
    path('api/sources/', views.api_sources, name='api_sources'),
    path('api/sources/<str:source_name>/capabilities/', views.api_source_capabilities, name='api_source_capabilities'),
    path('api/documentation/sources/', views.api_source_documentation, name='api_source_documentation'),
]
