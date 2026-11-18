from django.db import models
from django.utils import timezone


class Pedido(models.Model):
    """Una compra de lote que puede contener varias prendas del inventario."""

    nombre = models.CharField(max_length=120)
    importe_compra = models.DecimalField(max_digits=10, decimal_places=2)
    gastos_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateField(default=timezone.localdate)
    notas = models.CharField(max_length=255, blank=True)

    @property
    def inversion_total(self):
        return self.importe_compra + self.gastos_extra

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['-fecha', '-id']

class Prenda(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('disponible', 'Disponible'),
        ('vendido', 'Vendido'),
    ]

    tipo_de_prenda = models.CharField(max_length=100)
    talla = models.CharField(max_length=10, blank=True)
    color = models.CharField(max_length=50, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    donde_esta_subido = models.CharField(max_length=200)
    precio_comprado = models.DecimalField(max_digits=8, decimal_places=2)
    precio_vendido = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    localizador = models.CharField(max_length=10, blank=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.SET_NULL, null=True, blank=True, related_name='prendas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Se rellena sola al marcarla como vendida; las ventas anteriores a este
    # campo no tienen fecha.
    fecha_venta = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.estado == 'vendido' and self.fecha_venta is None:
            # Solo cuando pasa a vendida ahora, no al editar una venta antigua.
            anterior = Prenda.objects.filter(pk=self.pk).values_list('estado', flat=True).first() if self.pk else None
            if anterior != 'vendido':
                self.fecha_venta = timezone.now()
        elif self.estado != 'vendido':
            self.fecha_venta = None
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'estado' in update_fields:
            kwargs['update_fields'] = set(update_fields) | {'fecha_venta'}
        super().save(*args, **kwargs)

    def beneficio(self):
        if self.precio_vendido is not None:
            return self.precio_vendido - self.precio_comprado
        return None

    def __str__(self):
        return self.tipo_de_prenda
    
    class Meta:
        ordering = ['-id']
    
class Gasto(models.Model):
    concepto = models.CharField(max_length=200)
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    notas = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.concepto} - {self.importe}€"

    class Meta:
        ordering = ['-fecha']
