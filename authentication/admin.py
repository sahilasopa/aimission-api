from django.contrib import admin
from .models import *

admin.site.site_header = "Carbonix Admin Panel"


@admin.register(CarboUser)
class CarboUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number']


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ['tag']


@admin.register(Category)
class ModelNameAdmin(admin.ModelAdmin):
    list_display = ['category']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'tokens_accumulated']


@admin.register(StationProfile)
class StationProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'city', 'country']
    readonly_fields = ['id']


@admin.register(StationQRCode)
class StationQRCodeAdmin(admin.ModelAdmin):
    list_display = ['station', 'qrcode']


@admin.register(Journey)
class PublicTravelAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'emission_saved']
