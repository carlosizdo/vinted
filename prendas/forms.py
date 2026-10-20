from django import forms
from .models import Gasto, Pedido, Prenda

class PrendaForm(forms.ModelForm):
    class Meta:
        model = Prenda
        fields = ['tipo_de_prenda', 'talla', 'color', 'marca', 'localizador', 'donde_esta_subido', 'precio_comprado', 'precio_vendido', 'estado', 'pedido']
        widgets = {
            'pedido': forms.Select(attrs={'class': 'form-select'}),
        }

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


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['nombre', 'importe_compra', 'gastos_extra', 'fecha', 'notas']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'importe_compra': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'gastos_extra': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notas': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_importe_compra(self):
        importe = self.cleaned_data['importe_compra']
        if importe <= 0:
            raise forms.ValidationError('El importe de compra debe ser mayor que cero.')
        return importe

    def clean_gastos_extra(self):
        gastos = self.cleaned_data['gastos_extra']
        if gastos < 0:
            raise forms.ValidationError('Los gastos extra no pueden ser negativos.')
        return gastos


class ImportarPrendasForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo de inventario',
        help_text='Selecciona el Excel descargado desde “Exportar Excel”.',
    )

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('El archivo debe ser un Excel con extensión .xlsx.')
        if archivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('El archivo no puede superar 5 MB.')
        return archivo
