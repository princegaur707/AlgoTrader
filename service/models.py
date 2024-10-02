from django.db import models
import uuid

class StockData(models.Model):
    isin_code = models.CharField(max_length=12, primary_key=True)
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    series = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.company_name} ({self.symbol})"

class FinancialMetric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_name = models.CharField(max_length=100)

    def __str__(self):
        return self.metric_name

class FinancialData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(StockData, on_delete=models.CASCADE, related_name='financial_data')
    metric = models.ForeignKey(FinancialMetric, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=20, decimal_places=3, null=True)
    date = models.DateField()
    period = models.CharField(max_length=20, choices=(('annual', 'Annual'), ('quarterly', 'Quarterly')), default="annual")

    def __str__(self):
        return f"{self.stock.symbol} - {self.metric.metric_name} - {self.date} ({self.period})"
