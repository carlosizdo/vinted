from django.db import models

class Prenda(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('disponible', 'Disponible'),
        ('vendido', 'Vendido'),
    ]

    tipo_de_prenda = models.CharField(max_length=100)
    talla = models.CharField(max_length=10)
    color = models.CharField(max_length=50)
    marca = models.CharField(max_length=100)
    donde_esta_subido = models.CharField(max_length=200)
    precio_comprado = models.DecimalField(max_digits=8, decimal_places=2)
    precio_vendido = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    localizador = models.CharField(max_length=10, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

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
