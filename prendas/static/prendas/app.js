// Los avisos («Prenda vendida», etc.) se cierran solos a los 4 segundos.
setTimeout(function () {
    document.querySelectorAll('.toast-messages .alert').forEach(function (aviso) {
        bootstrap.Alert.getOrCreateInstance(aviso).close();
    });
}, 4000);
(function () {
    var modal = document.getElementById('modalVendida');
    if (!modal) return;
    modal.addEventListener('show.bs.modal', function (event) {
        var boton = event.relatedTarget;
        modal.querySelector('form').action = boton.dataset.url;
        modal.querySelector('.modal-title').textContent = boton.dataset.nombre;
        modal.querySelector('#compraVendida').textContent = 'La compraste por ' + boton.dataset.compra;
        modal.querySelector('#precioVendida').value = '';
        modal.querySelector('#nextVendida').value = window.location.pathname + window.location.search + '#prenda-' + boton.dataset.id;
    });
    modal.addEventListener('shown.bs.modal', function () {
        modal.querySelector('#precioVendida').focus();
    });
})();

// Botón «+» de la barra inferior: en el inventario abre el formulario sin recargar.
(function () {
    var formulario = document.getElementById('formNueva');
    function enfocar() {
        formulario.scrollIntoView({ behavior: 'smooth', block: 'start' });
        var campo = formulario.querySelector('input[name="tipo_de_prenda"]');
        if (campo) setTimeout(function () { campo.focus({ preventScroll: true }); }, 250);
    }
    document.querySelectorAll('[data-nueva-prenda]').forEach(function (boton) {
        boton.addEventListener('click', function (event) {
            if (!formulario) return; // En otras páginas, el enlace lleva al inventario.
            event.preventDefault();
            bootstrap.Collapse.getOrCreateInstance(formulario, { toggle: false }).show();
            enfocar();
        });
    });
    if (formulario && formulario.classList.contains('show') && window.location.hash === '#formNueva') enfocar();
})();
