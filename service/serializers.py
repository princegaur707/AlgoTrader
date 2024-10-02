from rest_framework import serializers
from .models import StockData, FinancialMetric, FinancialData


class StockDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockData
        fields = ['isin_code', 'company_name', 'industry', 'symbol', 'series']


class FinancialMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialMetric
        fields = ['id', 'metric_name']


class FinancialDataSerializer(serializers.ModelSerializer):
    stock = serializers.StringRelatedField()
    metric = serializers.StringRelatedField()

    class Meta:
        model = FinancialData
        fields = ['id', 'stock', 'metric', 'value', 'date', 'period']
