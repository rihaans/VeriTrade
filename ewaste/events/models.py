from django.utils.timezone import now
from django.db import models
from django.contrib.auth.models import User
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.dispatch import receiver
from django.db.models.signals import post_save

PRODUCT_CATEGORIES = [
    ('MOB_TAB', 'Mobiles and Tablets'),
    ('LAP_COMP', 'Laptops and Computers'),
    ('TV_MON', 'Televisions and Monitors'),
    ('HOME_APP', 'Home Appliances'),
    ('COMP_ACC', 'Computer Accessories'),
    ('GAM_CON', 'Gaming Consoles'),
    ('AUD_VID', 'Audio and Video Devices'),
    ('NET_DEV', 'Networking Devices'),
    ('STO_DEV', 'Storage Devices'),
    ('CAM_CORD', 'Cameras and Camcorders'),
    ('WEAR', 'Wearables'),
    ('OFF_EQUIP', 'Office Equipment'),
    ('IND_ELEC', 'Industrial Electronics'),
    ('MED_DEV', 'Medical Devices'),
    ('MISC', 'Miscellaneous Electronics'),
]

class userFull(models.Model):
    userFull_id = models.BigAutoField(primary_key=True, auto_created=True)
    userFull_image = models.ImageField(
        null=True, blank=True, 
        upload_to='user_photos/', 
        default='user_photos/default.png'  # Set default placeholder
    )
    userFull_phoneNumber = models.CharField(max_length=15, unique=True, null=True)

    # Address Fields
    userFull_street = models.CharField(max_length=255, null=True, blank=True)
    userFull_city = models.CharField(max_length=100, null=True, blank=True)
    userFull_state = models.CharField(max_length=100, null=True, blank=True)
    userFull_zipcode = models.CharField(max_length=20, null=True, blank=True)
    userFull_country = models.CharField(max_length=100, null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='userFull')

    class Meta:
        db_table = 'Full User'

    def _str_(self):
        return self.user.username

def product_image_upload_path(instance, filename, index):
    """Generate custom filename for product images"""
    ext = filename.split('.')[-1]  # Extract file extension

    if instance.pk:
        new_filename = f"product_{instance.pk}_{index}.{ext}"
    else:
        new_filename = f"temp_product_{index}.{ext}"  # Temporary filename before saving

    return os.path.join('product_photos/', new_filename)

class product(models.Model):
    product_id = models.BigAutoField(primary_key=True, auto_created=True)
    product_seller = models.ForeignKey(userFull, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100, null=True)
    
    product_category = models.CharField(max_length=10, choices=PRODUCT_CATEGORIES, default='OTH')
    product_description = models.CharField(max_length=5000)
    
    product_image_1 = models.ImageField(upload_to='product_photos/', null=True, blank=True)
    product_image_2 = models.ImageField(upload_to='product_photos/', null=True, blank=True)
    product_image_3 = models.ImageField(upload_to='product_photos/', null=True, blank=True)
    product_image_4 = models.ImageField(upload_to='product_photos/', null=True, blank=True)

    product_bought_price = models.IntegerField(null=True, default=0)
    product_bought_date = models.DateTimeField(null=True, blank=True)
    
    product_evaluation_status = models.IntegerField(null=True, default=0)
    product_evaluation_score = models.IntegerField(null=True, default=0)
    
    product_discount = models.IntegerField(default=0)
    product_sell_price = models.IntegerField(default=0)
    
    product_sold = models.IntegerField(default=0)
    product_onDelivery = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        """
        Override save() to rename images properly (both in DB and file system)
        """
        is_new = self.pk is None  # Check if this is a new object
        super().save(*args, **kwargs)  # Save first to get pk

        def rename_image(field, index):
            """Physically rename the image file in storage"""
            if field and hasattr(field, 'name') and field.name:
                old_path = field.path
                new_name = product_image_upload_path(self, field.name, index)
                new_path = os.path.join(default_storage.location, new_name)

                # Move and rename only if the file exists and is different
                if os.path.exists(old_path) and old_path != new_path:
                    os.rename(old_path, new_path)

                field.name = new_name  # Update DB reference

        updated_fields = []

        if self.product_image_1:
            rename_image(self.product_image_1, 1)
            updated_fields.append('product_image_1')
        if self.product_image_2:
            rename_image(self.product_image_2, 2)
            updated_fields.append('product_image_2')
        if self.product_image_3:
            rename_image(self.product_image_3, 3)
            updated_fields.append('product_image_3')
        if self.product_image_4:
            rename_image(self.product_image_4, 4)
            updated_fields.append('product_image_4')

        if updated_fields:
            super().save(update_fields=updated_fields)

    class Meta:
        db_table = 'Product'
    
class deliveryGuy(models.Model):
    deliveryGuy_id = models.BigAutoField(primary_key='True', auto_created='True')
    deliveryGuy_image = models.ImageField(null='True', upload_to='')
    deliveryGuy_phoneNumber = models.CharField(max_length=15, unique=True, null=False)
    currently_working = models.IntegerField(default=0)
    current_product = models.ForeignKey(product, on_delete=models.CASCADE, related_name="dlv_product", null=True)
    
    deliveryGuy_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deliveryGuy')

    class Meta:
        db_table = 'Delivery Guy'
        
class evaluatorGuy(models.Model):
    evaluatorGuy_id = models.BigAutoField(primary_key='True', auto_created='True')
    evaluatorGuy_image = models.ImageField(null='True', upload_to='')
    evaluatorGuy_phoneNumber = models.CharField(max_length=15, unique=True, null=False)
    
    currently_working = models.IntegerField(default=0)
    current_product = models.ForeignKey(product, on_delete=models.CASCADE, related_name="eval_product", null=True)
    evaluatorGuy_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluatorGuy')

    class Meta:
        db_table = 'Evaluator Guy'

class userCredits(models.Model):
    userCredits_id = models.BigAutoField(primary_key=True, auto_created=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    Credits = models.IntegerField(default=0)

    class Meta:
        db_table = 'User Credits'

# Signal to create userCredits when a new User is created
@receiver(post_save, sender=User)
def create_user_credits(sender, instance, created, **kwargs):
    if created:
        userCredits.objects.create(user=instance, Credits=0)

# Connect the signal
post_save.connect(create_user_credits, sender=User)
    
class deliveryJob(models.Model):
    deliveryJob_id = models.BigAutoField(primary_key='True', auto_created='True')
    deliveryJob_product = models.ForeignKey(product, on_delete=models.CASCADE)
    deliveryJob_seller = models.ForeignKey(userFull, on_delete=models.CASCADE, related_name='delivery_jobs_seller')
    deliveryJob_buyer = models.ForeignKey(userFull, on_delete=models.CASCADE, related_name='delivery_jobs_buyer')
    deliveryJob_deliveryGuy = models.ForeignKey(deliveryGuy, on_delete=models.CASCADE, null=True)
    deliveryJob_status = models.IntegerField(default=0)
    
class evaluatorJob(models.Model):
    evaluatorJob_id = models.BigAutoField(primary_key=True)
    evaluatorJob_product = models.ForeignKey(product, on_delete=models.CASCADE, null=True)
    evaluatorGuy = models.ForeignKey('evaluatorGuy', on_delete=models.CASCADE, null=True)
    evaluation_date = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        db_table = 'Evaluator Job'
    
    
class cart(models.Model):
    cart_id = models.BigAutoField(primary_key=True, auto_created=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    product = models.ForeignKey(product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=now)
    class Meta:
        unique_together = ('user', 'product') 

    def __str__(self):
        return f"{self.user.username} - {self.product.product_name} (x{self.quantity})"

    def total_price(self):
        return self.product.product_price * self.quantity
