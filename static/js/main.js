/**
 * Interacción global del layout Flowbite Dashboard (menú lateral, submenús,
 * persistencia en localStorage). Depende de jQuery y Bootstrap 4 (pestañas).
 */
var pathname = window.location.pathname;
var cuerpoDocumento = $('body');

function mostrarListaSubmenuLateral(nodoListaSubmenu) {
    nodoListaSubmenu.css('display', 'flex');
}

function ocultarListaSubmenuLateral(nodoListaSubmenu) {
    nodoListaSubmenu.hide();
}

var page = {
    components: {
        vertical: {
            claseBarraColapsada: 'app-sidebar--collapsed',
            claveBarraColapsada: 'factura_sidebar_colapsado',
            module_header: 'module_header',
            submodule: 'submodule',
            single_module: 'single_module',
        },
        horizontal: {
            module_header: 'module_header',
            single_module: 'single_module'
        }
    },
    initial: function () {
        var elemento = null;
        var colapso = this.components.vertical;

        // Sidebar colapsado en desktop
        if (localStorage.getItem(colapso.claveBarraColapsada)) {
            cuerpoDocumento.addClass(colapso.claseBarraColapsada);
        }

        // Restaurar módulo abierto en sidebar
        if (localStorage.getItem(colapso.module_header)) {
            elemento = cuerpoDocumento.find('li.nav-item[data-name="module_header"][data-id="' + localStorage.getItem(colapso.module_header) + '"]');
            if (elemento.length) {
                elemento.addClass('app-nav-branch--open');
                elemento.find('a.nav-link[data-name="module_header"]').addClass('active');
                mostrarListaSubmenuLateral(elemento.children('ul.app-nav-submenu'));
            } else {
                localStorage.removeItem(colapso.module_header);
            }
        }

        // Restaurar submodulo activo
        if (localStorage.getItem(colapso.submodule)) {
            elemento = cuerpoDocumento.find('li.nav-item .app-nav-submenu a.nav-link[data-name="submodule"][data-id="' + localStorage.getItem(colapso.submodule) + '"]');
            if (elemento.length) {
                elemento.addClass('active');
            } else {
                localStorage.removeItem(colapso.submodule);
            }
        }

        // Restaurar módulo individual activo
        if (localStorage.getItem(colapso.single_module)) {
            elemento = cuerpoDocumento.find('li.nav-item a.nav-link[data-name="single_module"][data-id="' + localStorage.getItem(colapso.single_module) + '"]');
            if (elemento.length) {
                elemento.addClass('active');
            } else {
                localStorage.removeItem(colapso.single_module);
            }
        }

        // Layout horizontal: restaurar pestaña activa
        if (localStorage.getItem(this.components.horizontal.module_header)) {
            elemento = $('.nav-tabs li.nav-item a[data-name="module_header"][href="' + localStorage.getItem(this.components.horizontal.module_header) + '"]');
            if (elemento.length && typeof elemento.tab === 'function') {
                elemento.tab('show');
                var contenedorPestanas = elemento.closest('ul.nav-tabs').parent().find('.tab-content');
                if (localStorage.getItem(this.components.horizontal.single_module)) {
                    var tarjetaModulo = contenedorPestanas.find('.tab-pane[data-id="' + localStorage.getItem(this.components.horizontal.module_header) + '"] a.card-icon[data-id="' + localStorage.getItem(this.components.horizontal.single_module) + '"]');
                    tarjetaModulo.addClass('card-icon-selected');
                }
            } else {
                localStorage.removeItem(this.components.horizontal.module_header);
                localStorage.removeItem(this.components.horizontal.single_module);
            }
        }
    }
};

$(function () {

    $('[data-toggle="tooltip"]').tooltip();

    $('.table')
        .on('draw.dt', function () {
            $('[data-toggle="tooltip"]').tooltip();
        })
        .on('click', 'img', function () {
            var rutaImagen = $(this).attr('src');
            load_image(rutaImagen);
        });

    // ===== LAYOUT VERTICAL: toggle del sidebar =====
    var colapso = page.components.vertical;

    $(document).on('click', '.collapsedMenu', function (evento) {
        evento.preventDefault();
        if ($(window).width() < 640) {
            // Móvil: toggle app-sidebar--open + backdrop
            var abierto = cuerpoDocumento.hasClass('app-sidebar--open');
            cuerpoDocumento.toggleClass('app-sidebar--open', !abierto);
            $('#sidebarBackdrop').toggleClass('hidden', abierto);
        } else {
            // Desktop: toggle app-sidebar--collapsed + persistir
            cuerpoDocumento.toggleClass(colapso.claseBarraColapsada);
            if (cuerpoDocumento.hasClass(colapso.claseBarraColapsada)) {
                localStorage.setItem(colapso.claveBarraColapsada, '1');
            } else {
                localStorage.removeItem(colapso.claveBarraColapsada);
            }
        }
    });

    // Cerrar sidebar al pulsar el backdrop (móvil)
    $('#sidebarBackdrop').on('click', function () {
        cuerpoDocumento.removeClass('app-sidebar--open');
        $(this).addClass('hidden');
    });

    // ===== NAVEGACIÓN DEL SIDEBAR =====
    var contenedorMenuLateral = $('.sidebar .app-nav-menu');
    if (contenedorMenuLateral.length) {
        contenedorMenuLateral
            .on('click', 'a.nav-link[data-name="single_module"]', function (evento) {
                evento.stopPropagation();
                var enlace = $(this);
                localStorage.removeItem(colapso.module_header);
                localStorage.removeItem(colapso.submodule);
                localStorage.setItem(colapso.single_module, String(enlace.data('id')));
            })
            .on('click', 'ul.app-nav-submenu a.nav-link[data-name="submodule"]', function (evento) {
                evento.stopPropagation();
                var enlace = $(this);
                localStorage.setItem(colapso.submodule, String(enlace.data('id')));
            })
            .on('click', 'a.nav-link[data-name="module_header"]', function (evento) {
                evento.preventDefault();
                evento.stopPropagation();
                var enlace = $(this);
                var filaModulo = enlace.parent('li.nav-item.app-nav-item--branch');
                if (!filaModulo.length) {
                    filaModulo = enlace.closest('li.nav-item');
                }
                var barraLateral = filaModulo.closest('.app-nav-menu');
                if (filaModulo.hasClass('app-nav-branch--open')) {
                    enlace.removeClass('active');
                    filaModulo.removeClass('app-nav-branch--open');
                    ocultarListaSubmenuLateral(filaModulo.children('ul.app-nav-submenu'));
                    localStorage.removeItem(colapso.module_header);
                } else {
                    barraLateral.find('li.app-nav-branch--open').each(function () {
                        var otraFila = $(this);
                        otraFila.find('a.nav-link[data-name="module_header"]').removeClass('active');
                        ocultarListaSubmenuLateral(otraFila.children('ul.app-nav-submenu'));
                        otraFila.removeClass('app-nav-branch--open');
                    });
                    enlace.addClass('active');
                    filaModulo.addClass('app-nav-branch--open');
                    mostrarListaSubmenuLateral(filaModulo.children('ul.app-nav-submenu'));
                    filaModulo.find('ul.app-nav-submenu a.nav-link[data-name="submodule"]').removeClass('active');
                    localStorage.setItem(colapso.module_header, String(filaModulo.data('id')));
                    localStorage.removeItem(colapso.submodule);
                }
                localStorage.removeItem(colapso.single_module);
                cuerpoDocumento.find('a.nav-link[data-name="single_module"]').removeClass('active');
            });
    }

    // ===== LAYOUT HORIZONTAL: pestañas de módulos =====
    $('.nav-tabs li.nav-item a[data-name="module_header"]').on('click', function () {
        var destinoPestaña = $(this).attr('href');
        localStorage.setItem(page.components.horizontal.module_header, destinoPestaña);
    });

    $('.tab-content .tab-pane a[data-name="single_module"]')
        .off('mouseenter mouseleave click')
        .on('mouseenter mouseleave', function () {
            $(this).closest('.tab-pane').find('a.card-icon-selected').removeClass('card-icon-selected');
        })
        .on('click', function () {
            localStorage.setItem(page.components.horizontal.single_module, $(this).data('id'));
        });

    // Logout: limpiar localStorage
    $('.btnLogout').on('click', function () {
        localStorage.clear();
    });

    // ===== LAYOUT HORIZONTAL: submenús anidados en navbar =====
    $('header.fb-header').on('click', '.dropdown-submenu .dropdown-menu', function (evento) {
        evento.stopPropagation();
    });

    $('header.fb-header').on('click', '.dropdown-submenu > .js-submenu-tipo-modulo', function (evento) {
        evento.preventDefault();
        evento.stopPropagation();
        var filaSubmenu = $(this).closest('.dropdown-submenu');
        if (window.matchMedia('(max-width: 767.98px)').matches) {
            var abierto = filaSubmenu.hasClass('submenu-abierto');
            filaSubmenu.siblings('.dropdown-submenu').removeClass('submenu-abierto');
            filaSubmenu.toggleClass('submenu-abierto', !abierto);
            $(this).attr('aria-expanded', filaSubmenu.hasClass('submenu-abierto'));
            filaSubmenu.siblings('.dropdown-submenu').find('.js-submenu-tipo-modulo').attr('aria-expanded', 'false');
        }
    });

    page.initial();
});
