from django.contrib import admin
from .models import Gasto, Pedido, Prenda


@admin.register(Prenda)
class PrendaAdmin(admin.ModelAdmin):
    list_display = ('tipo_de_prenda', 'marca', 'talla', 'estado', 'precio_comprado', 'precio_vendido', 'pedido', 'localizador')
    list_filter = ('estado', 'marca', 'talla', 'pedido')
    search_fields = ('tipo_de_prenda', 'marca', 'color', 'localizador')


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'importe', 'fecha')
    search_fields = ('concepto', 'notas')
    list_filter = ('fecha',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'importe_compra', 'gastos_extra', 'fecha')
    search_fields = ('nombre', 'notas')
    list_filter = ('fecha',)
