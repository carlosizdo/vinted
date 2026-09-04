from django import forms
from .models import Gasto, Prenda

class PrendaForm(forms.ModelForm):
    class Meta:
        model = Prenda
        fields = ['tipo_de_prenda', 'talla', 'color', 'marca', 'localizador', 'donde_esta_subido', 'precio_comprado', 'precio_vendido', 'estado']

    def clean(self):
        cleaned_data = super().clean()
        precio_comprado = cleaned_data.get('precio_comprado')
        precio_vendido = cleaned_data.get('precio_vendido')
        estado = cleaned_data.get('estado')

        if precio_comprado is not None and precio_comprado < 0:
            self.add_error('precio_comprado', 'El precio de compra no puede ser negativo.')
        if precio_vendido is not None and precio_vendido < 0:
            self.add_error('precio_vendido', 'El precio de venta no puede ser negativo.')
        if estado == 'vendido' and precio_vendido is None:
            self.add_error('precio_vendido', 'Indica el precio de venta para marcar la prenda como vendida.')

        return cleaned_data


class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['concepto', 'importe', 'notas']

    def clean_importe(self):
        importe = self.cleaned_data['importe']
        if importe <= 0:
            raise forms.ValidationError('El importe debe ser mayor que cero.')
        return importe
