from django.contrib import admin
from .models import Gasto, Prenda


@admin.register(Prenda)
class PrendaAdmin(admin.ModelAdmin):
    list_display = ('tipo_de_prenda', 'marca', 'talla', 'estado', 'precio_comprado', 'precio_vendido', 'localizador')
    list_filter = ('estado', 'marca', 'talla')
    search_fields = ('tipo_de_prenda', 'marca', 'color', 'localizador')


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'importe', 'fecha')
    search_fields = ('concepto', 'notas')
    list_filter = ('fecha',)
