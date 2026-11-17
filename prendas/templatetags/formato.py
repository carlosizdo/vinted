from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template

register = template.Library()

# Textos que se usan en el Excel para indicar "sin dato".
VALORES_VACIOS = {'', '-', '--', '---', '—', '–', 'n/a', 'na', 'none'}


@register.filter
def euros(valor):
    """Formatea un importe al estilo español: 1197.5 -> «1.197,50 €»."""
    if valor is None or valor == '':
        return '—'
    try:
        importe = Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return valor
    signo = '-' if importe < 0 else ''
    entero, decimales = f'{abs(importe):.2f}'.split('.')
    entero = f'{int(entero):,}'.replace(',', '.')
    return f'{signo}{entero},{decimales} €'


@register.filter
def dato(valor):
    """Devuelve el texto limpio, o cadena vacía si es un marcador de «sin dato»."""
    texto = str(valor if valor is not None else '').strip()
    return '' if texto.lower() in VALORES_VACIOS else texto
