from django.urls import path

from .views import (
    AgencyMarkCashPaidView,
    AgencyPaymentListView,
    CustomerPaymentListView,
    PaymentInvoiceView,
    PaymentReceiptView,
)

app_name = "payments-api"

urlpatterns = [
    path(
        "customer/",
        CustomerPaymentListView.as_view(),
        name="customer-list",
    ),
    path(
        "agency/",
        AgencyPaymentListView.as_view(),
        name="agency-list",
    ),
    path(
        "agency/<uuid:payment_id>/mark-paid/",
        AgencyMarkCashPaidView.as_view(),
        name="agency-mark-paid",
    ),
    path(
        "<uuid:payment_id>/invoice.pdf",
        PaymentInvoiceView.as_view(),
        name="invoice",
    ),
    path(
        "<uuid:payment_id>/receipt.pdf",
        PaymentReceiptView.as_view(),
        name="receipt",
    ),
]
