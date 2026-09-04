from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from io import BytesIO
import openpyxl

from .forms import GastoForm, PrendaForm
from .models import Gasto, Prenda


class PrendaFormTests(TestCase):
    def test_una_prenda_vendida_necesita_precio_de_venta(self):
        form = PrendaForm(data={
            'tipo_de_prenda': 'Chaqueta', 'talla': 'M', 'color': 'Negro',
            'marca': 'Marca', 'donde_esta_subido': 'Vinted',
            'precio_comprado': '10.00', 'estado': 'vendido',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('precio_vendido', form.errors)

    def test_un_gasto_debe_ser_positivo(self):
        form = GastoForm(data={'concepto': 'Bolsas', 'importe': '0', 'notas': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('importe', form.errors)


class InventarioViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='usuario', password='secreto')
        self.client.force_login(self.user)

    def test_panel_calcula_resultado_neto(self):
        Prenda.objects.create(
            tipo_de_prenda='Camiseta', talla='L', color='Azul', marca='Marca',
            donde_esta_subido='Vinted', precio_comprado=Decimal('10.00'),
            precio_vendido=Decimal('25.00'), estado='vendido',
        )
        response = self.client.get(reverse('lista_prendas'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['beneficio_total'], Decimal('15.00'))
        self.assertEqual(response.context['resultado_neto'], Decimal('15.00'))

    def test_resultado_neto_no_resta_gastos_extra(self):
        Prenda.objects.create(
            tipo_de_prenda='Camiseta', talla='L', color='Azul', marca='Marca',
            donde_esta_subido='Vinted', precio_comprado=Decimal('10.00'),
            precio_vendido=Decimal('25.00'), estado='vendido',
        )
        Gasto.objects.create(concepto='Bolsas', importe=Decimal('3.00'))

        response = self.client.get(reverse('lista_prendas'))

        self.assertEqual(response.context['resultado_neto'], Decimal('15.00'))

    def test_accion_masiva_pasa_prendas_a_disponible(self):
        prenda = Prenda.objects.create(
            tipo_de_prenda='Camiseta', talla='M', color='Negro', marca='Marca',
            donde_esta_subido='Vinted', precio_comprado=Decimal('10.00'), estado='borrador',
        )

        response = self.client.post(reverse('lista_prendas'), {
            'accion_masiva': 'disponible',
            'prendas': [str(prenda.pk)],
        })

        self.assertRedirects(response, reverse('lista_prendas'))
        prenda.refresh_from_db()
        self.assertEqual(prenda.estado, 'disponible')

    def test_exportacion_incluye_fecha_de_alta(self):
        Prenda.objects.create(
            tipo_de_prenda='Pantalón', talla='M', color='Gris', marca='Marca',
            donde_esta_subido='Vinted', precio_comprado=Decimal('12.00'), estado='disponible',
        )
        response = self.client.get(reverse('exportar_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_importacion_desde_excel_exportado(self):
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.append(['Tipo', 'Talla', 'Color', 'Marca', 'Localizador', 'Donde subido', 'Precio comprado', 'Precio vendido', 'Beneficio', 'Estado'])
        hoja.append(['Sudadera', 'M', 'Verde', 'Marca', 'A1', 'Vinted', 15, 30, 15, 'Vendido'])
        archivo = BytesIO()
        libro.save(archivo)
        archivo.seek(0)
        archivo.name = 'prendas.xlsx'

        response = self.client.post(reverse('importar_prendas'), {'archivo': archivo})
        self.assertRedirects(response, reverse('lista_prendas'))
        prenda = Prenda.objects.get(tipo_de_prenda='Sudadera')
        self.assertEqual(prenda.precio_vendido, Decimal('30'))
