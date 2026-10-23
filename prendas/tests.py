from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from io import BytesIO
import openpyxl

from .forms import GastoForm, PedidoForm, PrendaForm
from .models import Gasto, Pedido, Prenda


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

    def test_un_pedido_necesita_un_importe_positivo(self):
        form = PedidoForm(data={
            'nombre': 'Pedido de prueba', 'importe_compra': '0', 'gastos_extra': '0',
            'fecha': '2026-10-20', 'notas': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('importe_compra', form.errors)


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
        self.assertEqual(response.context['dinero_gastado'], Decimal('10.00'))

    def test_resultado_neto_no_resta_gastos_extra(self):
        Prenda.objects.create(
            tipo_de_prenda='Camiseta', talla='L', color='Azul', marca='Marca',
            donde_esta_subido='Vinted', precio_comprado=Decimal('10.00'),
            precio_vendido=Decimal('25.00'), estado='vendido',
        )
        Gasto.objects.create(concepto='Bolsas', importe=Decimal('3.00'))

        response = self.client.get(reverse('lista_prendas'))

        self.assertEqual(response.context['resultado_neto'], Decimal('15.00'))

    def test_panel_muestra_vista_de_tabla(self):
        Prenda.objects.create(
            tipo_de_prenda='Camiseta', talla='M', color='Negro', marca='Marca',
            donde_esta_subido='Vinted', precio_comprado=Decimal('10.00'), estado='disponible',
        )

        response = self.client.get(reverse('lista_prendas'), {'vista': 'tabla'})

        self.assertEqual(response.context['vista'], 'tabla')
        self.assertContains(response, '<table', html=False)

    def test_ordena_localizadores_numericos_antes_que_los_de_texto(self):
        for localizador in ('10', 'Caja P.', '2', ''):
            Prenda.objects.create(
                tipo_de_prenda=f'Prenda {localizador or "sin localizador"}', talla='M', color='Negro',
                marca='Marca', donde_esta_subido='Vinted', precio_comprado=Decimal('10.00'),
                estado='disponible', localizador=localizador,
            )

        response = self.client.get(reverse('lista_prendas'), {'orden': 'localizador'})

        self.assertEqual(
            [prenda.localizador for prenda in response.context['prendas'].object_list],
            ['2', '10', 'Caja P.', ''],
        )

    def test_editar_prenda_vuelve_al_filtro_anterior(self):
        prenda = Prenda.objects.create(
            tipo_de_prenda='Camiseta', talla='M', color='Azul', marca='Zara',
            donde_esta_subido='Vinted', precio_comprado=Decimal('10.00'), estado='disponible',
        )
        destino = '/?estado=disponible&marca=Zara&orden=localizador&vista=tabla'

        response = self.client.post(
            reverse('editar_prenda', args=[prenda.pk]),
            {
                'tipo_de_prenda': 'Camiseta actualizada', 'talla': 'M', 'color': 'Azul',
                'marca': 'Zara', 'donde_esta_subido': 'Vinted', 'localizador': '2',
                'precio_comprado': '10.00', 'precio_vendido': '', 'estado': 'disponible',
                'pedido': '', 'next': destino,
            },
        )

        self.assertRedirects(response, destino)

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

    def test_pedido_muestra_lo_recuperado_y_el_balance(self):
        pedido = Pedido.objects.create(nombre='Pedido de 600€', importe_compra=Decimal('600.00'))
        Prenda.objects.create(
            tipo_de_prenda='Cazadora', talla='M', color='Negro', marca='Marca',
            donde_esta_subido='Vinted', precio_comprado=Decimal('20.00'),
            precio_vendido=Decimal('45.00'), estado='vendido', pedido=pedido,
        )

        response = self.client.get(reverse('detalle_pedido', args=[pedido.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pedido'].facturacion, Decimal('45.00'))
        self.assertEqual(response.context['pedido'].pendiente_recuperar, Decimal('555.00'))
        self.assertEqual(response.context['pedido'].balance, Decimal('-555.00'))
