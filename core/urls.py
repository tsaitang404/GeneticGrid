from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('market/', views.market_view, name='market'),
    path('api/candlesticks/', views.api_candlesticks, name='api_candlesticks'),
    path('api/ticker/', views.api_ticker, name='api_ticker'),
    path('api/funding-rate/', views.api_funding_rate, name='api_funding_rate'),
    path('api/funding-rate/history/', views.api_funding_rate_history, name='api_funding_rate_history'),
    path('api/contract-basis/', views.api_contract_basis, name='api_contract_basis'),
    path('api/contract-basis/history/', views.api_contract_basis_history, name='api_contract_basis_history'),
    path('api/proxy-status/', views.api_proxy_status, name='api_proxy_status'),
    path('api/proxy-config/', views.api_proxy_config, name='api_proxy_config'),
    path('api/proxy-test/', views.api_proxy_test, name='api_proxy_test'),
    
    # 插件系统 API 端点
    path('api/sources/', views.api_sources, name='api_sources'),
    path('api/sources/<str:source_name>/capabilities/', views.api_source_capabilities, name='api_source_capabilities'),
    path('api/documentation/sources/', views.api_source_documentation, name='api_source_documentation'),
    path('api/positions/', views.api_positions, name='api_positions'),

    # 账户认证系统
    path('api/account/register/', views.api_account_register, name='api_account_register'),
    path('api/account/list/', views.api_account_list, name='api_account_list'),
    path('api/account/login/', views.api_account_login, name='api_account_login'),
    path('api/account/logout/', views.api_account_logout, name='api_account_logout'),
    path('api/account/refresh/', views.api_account_refresh, name='api_account_refresh'),
    path('api/account/session/', views.api_account_session, name='api_account_session'),
    path('api/account/balance/', views.api_account_balance, name='api_account_balance'),
    path('api/account/positions/', views.api_account_positions, name='api_account_positions'),
    path('api/account/symbols/', views.api_account_symbols, name='api_account_symbols'),
    path('api/account/<int:account_id>/', views.api_account_delete, name='api_account_delete'),
    path('api/account/place-order/', views.api_account_place_order, name='api_account_place_order'),
    path('api/account/cancel-order/', views.api_account_cancel_order, name='api_account_cancel_order'),
    
    # 期权数据
    path('api/options/instruments/', views.api_option_instruments, name='api_option_instruments'),
    path('api/options/ticker/', views.api_option_ticker, name='api_option_ticker'),
]
