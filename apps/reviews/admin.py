from django.contrib import admin

from .models import (
    AgencyCustomerRating,
    CustomerRentalReview,
)

admin.site.register(CustomerRentalReview)
admin.site.register(AgencyCustomerRating)
