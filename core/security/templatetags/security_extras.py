from django import template
from django.forms import CheckboxInput

from core.security.models import Module
from core.security.models import ModuleType

register = template.Library()


@register.filter
def get_module_type(group_id):
    return ModuleType.objects.filter(module__groupmodule__group_id=group_id, is_active=True).distinct().order_by(
        'name')


@register.filter
def get_module_types_con_modulos(group_id):
    """
    Tipos de módulo del grupo que tienen al menos un enlace vertical u horizontal.
    Evita cabeceras o pestañas vacías (misma lógica que el menú lateral corregido).
    """
    tipos_ordenados = ModuleType.objects.filter(
        module__groupmodule__group_id=group_id,
        is_active=True,
    ).distinct().order_by('name')
    tipos_con_enlaces = []
    for tipo_modulo in tipos_ordenados:
        if tipo_modulo.get_modules_vertical().exists() or tipo_modulo.get_modules_horizontal().exists():
            tipos_con_enlaces.append(tipo_modulo)
    return tipos_con_enlaces


@register.filter()
def get_module_horizontal(group):
    return Module.objects.filter(groupmodule__group_id=group, module_type_id=None, is_active=True,
                                 is_vertical=False).order_by('name')


@register.filter()
def is_checkbox(field):
    return field.field.widget.__class__.__name__ == CheckboxInput().__class__.__name__