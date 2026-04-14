from datetime import datetime
from decimal import Decimal

from core.pos.models import Company
from core.security.models import Dashboard

# Imagen mínima (1×1 px transparente) para favicon/logo cuando no hay archivo en BD ni en static.
_IMAGEN_URI_POR_DEFECTO = (
    'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
)


class DashboardPlantillaPorDefecto:
    """
    Sustituto cuando no existe registro Dashboard en BD.
    Expone las mismas propiedades que usan base.html, cabeceras, sidebar y login.
    """

    name = 'FACTURASAPP'
    navbar = 'navbar-dark navbar-primary'
    sidebar = 'sidebar-dark-primary'
    brand_logo = ''
    card = 'card-primary'

    def get_image(self):
        """URL para favicon y logos cuando no hay imagen configurada."""
        return _IMAGEN_URI_POR_DEFECTO

    def get_icon(self):
        """Icono Font Awesome para pantallas de autenticación."""
        return 'fa-solid fa-file-invoice'


class EmpresaPlantillaPorDefecto:
    """
    Sustituto cuando no hay empresa en BD (evita errores en dashboard cliente y plantillas POS).
    """

    name = ''
    ruc = ''
    address = ''
    mobile = ''
    phone = ''
    email = ''
    website = ''
    iva = Decimal('12.00')

    def get_image(self):
        return _IMAGEN_URI_POR_DEFECTO


def system_information(request):
    """
    Contexto global: dashboard, menú según diseño, empresa y fecha.
    Garantiza objetos sustitutos si las tablas están vacías (instalación nueva o pruebas).
    """
    dashboard_bd = Dashboard.objects.first()
    if dashboard_bd is None:
        dashboard = DashboardPlantillaPorDefecto()
        plantilla_menu = 'hzt_body.html'
    else:
        dashboard = dashboard_bd
        plantilla_menu = dashboard.get_template_from_layout()

    empresa_bd = Company.objects.first()
    empresa = empresa_bd if empresa_bd is not None else EmpresaPlantillaPorDefecto()

    return {
        'dashboard': dashboard,
        'date_joined': datetime.now(),
        'menu': plantilla_menu,
        'company': empresa,
    }
