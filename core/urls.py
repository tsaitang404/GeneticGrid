from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('market/', views.market_view, name='market'),
    path('api/candlesticks/', views.api_candlesticks, name='api_candlesticks'),
    path('api/ticker/', views.api_ticker, name='api_ticker'),
    path('api/proxy-status/', views.api_proxy_status, name='api_proxy_status'),
]
