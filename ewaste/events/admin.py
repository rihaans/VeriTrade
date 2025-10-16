from django.contrib import admin
from .models import (
    userFull, product, deliveryGuy, evaluatorGuy, 
    userCredits, deliveryJob, evaluatorJob, cart
)

# Registering all models
admin.site.register(userFull)
admin.site.register(product)
admin.site.register(deliveryGuy)
admin.site.register(evaluatorGuy)
admin.site.register(userCredits)
admin.site.register(deliveryJob)
admin.site.register(evaluatorJob)
admin.site.register(cart)
