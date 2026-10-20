# Generated manually to keep the schema change explicit and reviewable.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prendas', '0005_prenda_fecha_creacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120)),
                ('importe_compra', models.DecimalField(decimal_places=2, max_digits=10)),
                ('gastos_extra', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('fecha', models.DateField(default=django.utils.timezone.localdate)),
                ('notas', models.CharField(blank=True, max_length=255)),
            ],
            options={'ordering': ['-fecha', '-id']},
        ),
        migrations.AddField(
            model_name='prenda',
            name='pedido',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prendas', to='prendas.pedido'),
        ),
    ]
