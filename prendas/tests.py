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


class FormatoTests(TestCase):
    def test_euros_usa_formato_espanol(self):
        from .templatetags.formato import euros
        self.assertEqual(euros(Decimal('1197.17')), '1.197,17 €')
        self.assertEqual(euros(Decimal('6.8')), '6,80 €')
        self.assertEqual(euros(Decimal('-555')), '-555,00 €')
        self.assertEqual(euros(None), '—')

    def test_dato_oculta_marcadores_vacios(self):
        from .templatetags.formato import dato
        for vacio in ('-', '--', ' — ', '', None):
            self.assertEqual(dato(vacio), '')
        self.assertEqual(dato(' XL '), 'XL')


class TarjetasInventarioTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(username='usuario', password='secreto'))

    def test_muestra_24_prendas_por_pagina(self):
        for i in range(30):
            Prenda.objects.create(
                tipo_de_prenda=f'Prenda {i}', talla='M', color='Negro', marca='Marca',
                donde_esta_subido='Vinted', precio_comprado=Decimal('5.00'), estado='disponible',
            )
        response = self.client.get(reverse('lista_prendas'))
        self.assertEqual(len(response.context['prendas'].object_list), 24)

    def test_tarjeta_oculta_datos_vacios_y_muestra_precio_de_compra(self):
        Prenda.objects.create(
            tipo_de_prenda='Falda azul', talla='-', color='-', marca='-', localizador='--',
            donde_esta_subido='Vinted', precio_comprado=Decimal('1234.50'), estado='disponible',
        )
        response = self.client.get(reverse('lista_prendas'))
        self.assertNotContains(response, 'Talla -')
        self.assertNotContains(response, '📍 --')
        self.assertContains(response, '1.234,50 €')


class MarcarVendidaTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(username='usuario', password='secreto'))
        self.prenda = Prenda.objects.create(
            tipo_de_prenda='Chaqueta', talla='M', color='Negro', marca='Zara',
            donde_esta_subido='Vinted', precio_comprado=Decimal('5.00'), estado='disponible',
        )

    def test_marca_vendida_con_precio_con_coma(self):
        response = self.client.post(
            reverse('marcar_vendida', args=[self.prenda.pk]),
            {'precio_vendido': '12,50', 'next': '/?estado=disponible'},
        )
        self.assertRedirects(response, '/?estado=disponible', fetch_redirect_response=False)
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.estado, 'vendido')
        self.assertEqual(self.prenda.precio_vendido, Decimal('12.50'))

    def test_acepta_punto_y_miles(self):
        self.client.post(reverse('marcar_vendida', args=[self.prenda.pk]), {'precio_vendido': '1.234,5 €'})
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.precio_vendido, Decimal('1234.50'))

    def test_precio_no_valido_no_cambia_la_prenda(self):
        for valor in ('', 'abc', '-3', 'NaN'):
            self.client.post(reverse('marcar_vendida', args=[self.prenda.pk]), {'precio_vendido': valor})
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.estado, 'disponible')
        self.assertIsNone(self.prenda.precio_vendido)

    def test_get_no_modifica_nada(self):
        self.client.get(reverse('marcar_vendida', args=[self.prenda.pk]))
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.estado, 'disponible')

    def test_editar_prenda_mantiene_el_precio_con_punto(self):
        self.prenda.precio_comprado = Decimal('12.50')
        self.prenda.save()
        response = self.client.get(reverse('editar_prenda', args=[self.prenda.pk]))
        self.assertContains(response, 'value="12.50"')
        self.assertNotContains(response, 'value="12,50"')

    def test_formulario_de_pedido_usa_fecha_iso(self):
        response = self.client.get(reverse('lista_pedidos'))
        self.assertRegex(response.content.decode(), r'name="fecha" value="\d{4}-\d{2}-\d{2}"')


class RevisionTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(username='usuario', password='secreto'))

    def crear(self, nombre, **extra):
        datos = dict(tipo_de_prenda=nombre, talla='M', color='Negro', marca='Zara',
                     donde_esta_subido='Vinted', precio_comprado=Decimal('5.00'), estado='disponible')
        datos.update(extra)
        return Prenda.objects.create(**datos)

    def test_orden_por_precio_deja_sin_vender_al_final(self):
        self.crear('Sin vender')
        self.crear('Barata', precio_vendido=Decimal('3.00'), estado='vendido')
        self.crear('Cara', precio_vendido=Decimal('50.00'), estado='vendido')
        for orden, esperado in (('precio_desc', ['Cara', 'Barata', 'Sin vender']),
                                ('precio_asc', ['Barata', 'Cara', 'Sin vender'])):
            response = self.client.get(reverse('lista_prendas'), {'orden': orden})
            nombres = [p.tipo_de_prenda for p in response.context['prendas'].object_list]
            self.assertEqual(nombres, esperado, orden)

    def test_desplegables_sin_repetidos_ni_guiones(self):
        for i, (talla, marca) in enumerate([('M', 'Zara'), ('M', 'Zara'), ('-', '-'), ('L', 'adidas')]):
            self.crear(f'P{i}', talla=talla, marca=marca)
        response = self.client.get(reverse('lista_prendas'))
        self.assertEqual(response.context['tallas'], ['L', 'M'])
        self.assertEqual(response.context['marcas'], ['adidas', 'Zara'])

    def test_se_puede_crear_prenda_sin_talla_color_ni_marca(self):
        response = self.client.post(reverse('lista_prendas'), {
            'tipo_de_prenda': 'Bolso', 'talla': '', 'color': '', 'marca': '',
            'donde_esta_subido': 'Vinted', 'precio_comprado': '4.00', 'estado': 'disponible',
        })
        self.assertRedirects(response, reverse('lista_prendas'))
        self.assertTrue(Prenda.objects.filter(tipo_de_prenda='Bolso', talla='').exists())

    def _importar(self, *filas):
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.append(['Tipo', 'Talla', 'Color', 'Marca', 'Localizador', 'Donde subido', 'Precio comprado', 'Precio vendido', 'Beneficio', 'Estado'])
        for fila in filas:
            hoja.append(fila)
        archivo = BytesIO()
        libro.save(archivo)
        archivo.seek(0)
        archivo.name = 'prendas.xlsx'
        return self.client.post(reverse('importar_prendas'), {'archivo': archivo})

    def test_importar_celdas_vacias_no_guarda_none(self):
        self._importar(['Gorra', None, None, None, None, 'Vinted', 2, None, None, 'Disponible'])
        prenda = Prenda.objects.get(tipo_de_prenda='Gorra')
        self.assertEqual((prenda.talla, prenda.color, prenda.marca, prenda.localizador), ('', '', '', ''))

    def test_importar_texto_demasiado_largo_da_mensaje_claro(self):
        response = self._importar(['Gorra', 'Talla única grande', 'Rojo', 'Nike', None, 'Vinted', 2, None, None, 'Disponible'])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'más de 10 caracteres')
        self.assertFalse(Prenda.objects.exists())

    def test_editar_vuelve_a_la_prenda(self):
        prenda = self.crear('Camisa')
        response = self.client.get(reverse('lista_prendas'))
        self.assertContains(response, f'%23prenda-{prenda.pk}')
        self.assertContains(response, f'id="prenda-{prenda.pk}"')

    def test_pagina_404_en_espanol(self):
        response = self.client.get('/no-existe/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'No encontramos esta página', status_code=404)


class PedidosMejorasTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(username='usuario', password='secreto'))
        self.pedido = Pedido.objects.create(nombre='Lote octubre', importe_compra=Decimal('100.00'),
                                            gastos_extra=Decimal('0.01'))

    def crear(self, nombre, **extra):
        datos = dict(tipo_de_prenda=nombre, talla='M', color='Negro', marca='Zara',
                     donde_esta_subido='Vinted', precio_comprado=Decimal('5.00'), estado='disponible')
        datos.update(extra)
        return Prenda.objects.create(**datos)

    def test_asignar_varias_prendas_a_la_vez(self):
        a, b = self.crear('A'), self.crear('B')
        otro = Pedido.objects.create(nombre='Otro', importe_compra=Decimal('10'))
        ocupada = self.crear('C', pedido=otro)
        response = self.client.get(reverse('asignar_prendas', args=[self.pedido.pk]))
        self.assertEqual({p.pk for p in response.context['prendas']}, {a.pk, b.pk})
        self.client.post(reverse('asignar_prendas', args=[self.pedido.pk]), {'prendas': [a.pk, b.pk, ocupada.pk]})
        self.assertEqual(set(self.pedido.prendas.values_list('pk', flat=True)), {a.pk, b.pk})
        ocupada.refresh_from_db()
        self.assertEqual(ocupada.pedido, otro)  # No se roba prendas de otros pedidos.

    def test_quitar_prenda_del_pedido_no_la_borra(self):
        prenda = self.crear('A', pedido=self.pedido)
        self.client.post(reverse('quitar_de_pedido', args=[self.pedido.pk, prenda.pk]))
        prenda.refresh_from_db()
        self.assertIsNone(prenda.pedido)

    def test_eliminar_pedido_conserva_prendas(self):
        prenda = self.crear('A', pedido=self.pedido)
        response = self.client.get(reverse('eliminar_pedido', args=[self.pedido.pk]))
        self.assertTrue(Pedido.objects.filter(pk=self.pedido.pk).exists())  # GET solo pregunta.
        self.client.post(reverse('eliminar_pedido', args=[self.pedido.pk]))
        self.assertFalse(Pedido.objects.filter(pk=self.pedido.pk).exists())
        prenda.refresh_from_db()
        self.assertIsNone(prenda.pedido)

    def test_repartir_coste_suma_exacta_y_solo_al_confirmar(self):
        prendas = [self.crear(f'P{i}', pedido=self.pedido) for i in range(3)]
        self.client.get(reverse('repartir_coste', args=[self.pedido.pk]))
        self.assertEqual(Prenda.objects.get(pk=prendas[0].pk).precio_comprado, Decimal('5.00'))
        self.client.post(reverse('repartir_coste', args=[self.pedido.pk]))
        nuevos = sorted(Prenda.objects.filter(pedido=self.pedido).values_list('precio_comprado', flat=True))
        self.assertEqual(sum(nuevos), Decimal('100.01'))
        self.assertEqual(nuevos, [Decimal('33.33'), Decimal('33.34'), Decimal('33.34')])

    def test_media_necesaria_por_prenda(self):
        self.crear('Vendida', pedido=self.pedido, precio_vendido=Decimal('20.01'), estado='vendido')
        for i in range(4):
            self.crear(f'P{i}', pedido=self.pedido)
        response = self.client.get(reverse('detalle_pedido', args=[self.pedido.pk]))
        self.assertEqual(response.context['pedido'].media_necesaria, Decimal('20.00'))
        self.assertContains(response, '20,00 €')

    def test_nueva_prenda_desde_pedido_vuelve_al_pedido(self):
        response = self.client.get(reverse('lista_prendas'), {'pedido': self.pedido.pk})
        self.assertEqual(response.context['form'].initial.get('pedido'), self.pedido)
        response = self.client.post(reverse('lista_prendas') + f'?pedido={self.pedido.pk}', {
            'tipo_de_prenda': 'Bolso', 'donde_esta_subido': 'Vinted', 'precio_comprado': '4.00',
            'estado': 'disponible', 'pedido': self.pedido.pk, 'volver_al_pedido': '1',
        })
        self.assertRedirects(response, reverse('detalle_pedido', args=[self.pedido.pk]))
        self.assertTrue(self.pedido.prendas.filter(tipo_de_prenda='Bolso').exists())


class DisenoYResumenTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(username='usuario', password='secreto'))

    def crear(self, nombre, **extra):
        datos = dict(tipo_de_prenda=nombre, talla='M', color='Negro', marca='Zara',
                     donde_esta_subido='Vinted', precio_comprado=Decimal('5.00'), estado='disponible')
        datos.update(extra)
        return Prenda.objects.create(**datos)

    def test_fecha_de_venta_se_pone_al_vender_y_se_quita_al_deshacer(self):
        prenda = self.crear('A')
        self.assertIsNone(prenda.fecha_venta)
        self.client.post(reverse('marcar_vendida', args=[prenda.pk]), {'precio_vendido': '9'})
        prenda.refresh_from_db()
        self.assertIsNotNone(prenda.fecha_venta)
        prenda.estado = 'disponible'
        prenda.save()
        prenda.refresh_from_db()
        self.assertIsNone(prenda.fecha_venta)

    def test_editar_venta_antigua_no_le_pone_fecha(self):
        prenda = self.crear('Antigua', precio_vendido=Decimal('9'), estado='vendido')
        Prenda.objects.filter(pk=prenda.pk).update(fecha_venta=None)  # Como las ventas de antes.
        prenda.refresh_from_db()
        prenda.color = 'Rojo'
        prenda.save()
        prenda.refresh_from_db()
        self.assertIsNone(prenda.fecha_venta)

    def test_resumen_calcula_cifras_y_marcas(self):
        self.crear('A', marca='Nike', precio_vendido=Decimal('20'), estado='vendido')
        self.crear('B', marca='nike', precio_vendido=Decimal('10'), estado='vendido')
        self.crear('C', marca='-', precio_vendido=Decimal('8'), estado='vendido')
        self.crear('D')
        Gasto.objects.create(concepto='Bolsas', importe=Decimal('3'))
        response = self.client.get(reverse('resumen'))
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertEqual(ctx['beneficio'], Decimal('23.00'))
        self.assertEqual(ctx['beneficio_tras_gastos'], Decimal('20.00'))
        self.assertEqual(ctx['n_stock'], 1)
        self.assertEqual([(m['nombre'], m['n']) for m in ctx['top_marcas']], [('Nike', 2)])
        self.assertEqual(sum(ctx['grafica']['vendidas']), 3)
        self.assertEqual(len(ctx['grafica']['meses']), 6)

    def test_paginas_cargan_con_iconos_y_sin_emojis(self):
        prenda = self.crear('A')
        pedido = Pedido.objects.create(nombre='Lote', importe_compra=Decimal('10'))
        for url in (reverse('lista_prendas'), reverse('lista_pedidos'), reverse('detalle_pedido', args=[pedido.pk]),
                    reverse('lista_gastos'), reverse('resumen'), reverse('lista_prendas') + '?vista=tabla'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertContains(response, 'tabler-icons')
            for emoji in ('🗑', '✏', '📦', '💸'):
                self.assertNotContains(response, emoji)

    def test_boton_mas_abre_el_formulario(self):
        response = self.client.get(reverse('lista_prendas'), {'nuevo': '1'})
        self.assertTrue(response.context['abrir_nuevo'])
        self.assertContains(response, 'class="collapse show" id="formNueva"')


class TodasLasPaginasCarganTests(TestCase):
    """Abre cada página con sesión iniciada para detectar errores de plantilla."""

    def test_todas_las_paginas_responden(self):
        self.client.force_login(User.objects.create_user(username='usuario', password='secreto'))
        pedido = Pedido.objects.create(nombre='Lote', importe_compra=Decimal('10'))
        prenda = Prenda.objects.create(tipo_de_prenda='A', donde_esta_subido='Vinted', precio_comprado=Decimal('5'),
                                       estado='disponible', pedido=pedido)
        gasto = Gasto.objects.create(concepto='Bolsas', importe=Decimal('3'))
        urls = [
            reverse('lista_prendas'), reverse('lista_prendas') + '?vista=tabla', reverse('editar_prenda', args=[prenda.pk]),
            reverse('eliminar_prenda', args=[prenda.pk]), reverse('importar_prendas'), reverse('lista_gastos'),
            reverse('eliminar_gasto', args=[gasto.pk]), reverse('lista_pedidos'), reverse('detalle_pedido', args=[pedido.pk]),
            reverse('editar_pedido', args=[pedido.pk]), reverse('asignar_prendas', args=[pedido.pk]),
            reverse('eliminar_pedido', args=[pedido.pk]), reverse('repartir_coste', args=[pedido.pk]), reverse('resumen'),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        # Con un aviso pendiente (las plantillas de avisos fallaron una vez).
        self.client.post(reverse('lista_gastos'), {'concepto': 'Cinta', 'importe': '2'})
        self.assertEqual(self.client.get(reverse('lista_gastos')).status_code, 200)

    def test_inicio_de_sesion_carga(self):
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)
