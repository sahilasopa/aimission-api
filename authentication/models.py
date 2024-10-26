import base64
import json
import os
import uuid
from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.conf import settings
from django.core.files import File
from django.db import models
import qrcode
from math import cos, asin, sqrt, pi

CREDITS_PER_KM = 0.01
PUBLIC_TRANSPORT_TYPES = (
    ('Metro', "Metro"),
    ('Bus', "Bus"),
    ('Train', "Train"),
)


class CarboUser(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    dob = models.DateField(null=True)
    crypto_id = models.CharField(max_length=255)


class Tags(models.Model):
    tag = models.CharField(max_length=255)

    def __str__(self):
        return self.tag

    class Meta:
        verbose_name_plural = 'Tags'


class Category(models.Model):
    category = models.CharField(max_length=255)

    def __str__(self):
        return self.category

    class Meta:
        verbose_name_plural = 'Categories'


class Product(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='products')
    price = models.DecimalField(max_digits=9, decimal_places=8)
    tags = models.ManyToManyField(Tags)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)


class Wishlist(models.Model):
    user = models.ForeignKey(CarboUser, on_delete=models.CASCADE)
    product = models.ManyToManyField(Product)
    tokens_accumulated = models.DecimalField(max_digits=9, decimal_places=8, default=0)


class StationProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=PUBLIC_TRANSPORT_TYPES)
    latitude = models.DecimalField(max_digits=12, decimal_places=8)
    longitude = models.DecimalField(max_digits=12, decimal_places=8)
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class StationQRCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(StationProfile, on_delete=models.CASCADE)
    qrcode = models.ImageField(upload_to='qr', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.qrcode:
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.jpg')
            logo = Image.open(logo_path)
            wpercent = (120 / float(logo.size[0]))
            hsize = int((float(logo.size[1]) * float(wpercent)))
            logo = logo.resize((120, hsize), Image.ANTIALIAS)
            QRcode = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_H
            )
            encoded_id = base64.b64encode(bytes(f'{self.station.id}', 'utf-8')).decode('utf-8')
            json_data = json.dumps({"station_id": str(encoded_id), "name": self.station.name, "type": self.station.type})
            QRcode.add_data(json_data)
            QRcode.make()
            QRcolor = '#c3dc34'
            QRimg = QRcode.make_image(fill_color=QRcolor, back_color="white").convert('RGB')
            pos = ((QRimg.size[0] - logo.size[0]) // 2,
                   (QRimg.size[1] - logo.size[1]) // 2)
            QRimg.paste(logo, pos)
            stream = BytesIO()
            QRimg.save(stream, quality=90, format='PNG')
            self.qrcode.save(f'{self.id}qrcode.png', File(stream), save=False)
        super(StationQRCode, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Station QR Codes'


class Journey(models.Model):
    user = models.ForeignKey(CarboUser, on_delete=models.CASCADE, null=True)
    type = models.CharField(max_length=255)
    start_stop = models.ForeignKey(StationProfile, max_length=255, on_delete=models.SET_NULL, null=True, related_name="start_stop")
    end_stop = models.ForeignKey(StationProfile, max_length=255, on_delete=models.SET_NULL, null=True, related_name="end_stop")
    distance = models.DecimalField(max_digits=19, decimal_places=8, default=0)
    start_time = models.DateTimeField(auto_created=True)
    end_time = models.DateTimeField(null=True)
    in_progress = models.BooleanField(default=True)
    emission_saved = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    credits = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    def get_credits(self):
        if self.end_stop and self.start_stop:
            self.credits = self.calculate_credits()
            super(Journey, self).save()
            return self.calculate_credits()

    def calculate_credits(self):
        return float(self.distance) * CREDITS_PER_KM

    def calculate_carbon_emissions_saved(self):
        self.emission_saved = (float(self.distance) * 0.03) * 1000.00
        super(Journey, self).save()
        return self.emission_saved

    def calculate_time_taken(self):
        return (self.end_time.replace(tzinfo=None) - self.start_time.replace(tzinfo=None)).seconds

    def save(self, *args, **kwargs):
        if self.start_stop and self.end_stop:
            self.distance = self.calculate_distance()
        super(Journey, self).save(*args, **kwargs)

    def calculate_distance(self):
        lat1 = self.start_stop.latitude
        lat2 = self.end_stop.latitude
        lon1 = self.start_stop.longitude
        lon2 = self.end_stop.longitude
        r = 6371
        p = Decimal(pi / 180).quantize(Decimal("1.00000"))

        a = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
        return 2 * r * asin(sqrt(a))
