"""
URL configuration for stocks project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from service.views import HistoricalDataView, MarketDataView, FundamentalView, StocksDataView, FinancialDataView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('historical-data/', HistoricalDataView.as_view(), name='historical-data'),
    path('market-data/', MarketDataView.as_view(), name="market-data"),
    path('fundamental-data/', FundamentalView.as_view(), name="fundamental-data"),
    path('stocks-data/', StocksDataView.as_view(), name="stocks-data"),
    path('financial-data/annual/', FinancialDataView.as_view(), name="financial-data", kwargs={'period': 'annual'}),
    path('financial-data/quarterly/', FinancialDataView.as_view(), name="financial-data", kwargs={'period': 'quarterly'})
]


