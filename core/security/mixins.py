from crum import get_current_request
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator

from config import settings
from core.security.models import Module


def variantes_ruta_para_coincidir(ruta):
    """
    Genera variantes con/sin barra final para comparar con Module.url.

    Evita que falle el acceso si la petición y la BD difieren solo en la '/'.
    """
    if not ruta:
        return {'/'}
    ruta = ruta.strip() or '/'
    conjunto = {ruta}
    sin_barra = ruta.rstrip('/')
    if sin_barra and sin_barra != ruta:
        conjunto.add(sin_barra)
    if not ruta.endswith('/'):
        conjunto.add(ruta + '/')
    return conjunto


def serializar_modulo_para_sesion(modulo):
    """
    Convierte un Module a un dict compatible con JSONSerializer.

    Las plantillas usan request.session.module.url, .name y .get_icon;
    con un dict, el motor de plantillas de Django resuelve esas claves
    igual que atributos (p. ej. modulo['get_icon'] vía .get_icon).
    """
    if modulo is None:
        return None
    return {
        'id': modulo.pk,
        'url': modulo.url,
        'name': modulo.name,
        'get_icon': modulo.get_icon(),
    }


class ModuleMixin(object):

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        request.session['module'] = None
        try:
            request.user.set_group_session()
            id_grupo = request.user.get_group_id_session()
            if not id_grupo:
                messages.error(
                    request,
                    'No tiene un perfil de grupo asignado; asigne grupos al usuario en el admin.',
                )
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            rutas_posibles = variantes_ruta_para_coincidir(request.path)
            modules = Module.objects.filter(Q(module_type__is_active=True) | Q(module_type__isnull=True)).filter(
                groupmodule__group_id__in=[id_grupo], is_active=True, url__in=rutas_posibles, is_visible=True
            )
            if modules.exists():
                request.session['module'] = serializar_modulo_para_sesion(modules[0])
                return super().get(request, *args, **kwargs)
            else:
                messages.error(request, 'No tiene permiso para ingresar a este módulo')
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        except Exception:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)


class PermissionMixin(object):
    permission_required = None

    def get_permits(self):
        """
        Lista de códigos de permiso requeridos. Soporta str, tupla/lista o None
        (lista vacía: no se exige permiso concreto para la comprobación por índice).
        """
        permisos_requeridos = self.permission_required
        if permisos_requeridos is None:
            return []
        if isinstance(permisos_requeridos, str):
            return [permisos_requeridos]
        try:
            return list(permisos_requeridos)
        except TypeError:
            return []

    def get_last_url(self):
        request = get_current_request()
        if 'url_last' in request.session:
            return request.session['url_last']
        return settings.LOGIN_REDIRECT_URL

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        request.session['module'] = None
        try:
            request.user.set_group_session()
            datos_grupo = request.session.get('group')
            # Clave ausente, None o dict inválido: no se puede comprobar permisos por grupo.
            if not isinstance(datos_grupo, dict) or datos_grupo.get('id') is None:
                messages.error(
                    request,
                    'No tiene un perfil de grupo asignado; asigne grupos al usuario en el admin.',
                )
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            grupo = Group.objects.get(pk=datos_grupo['id'])
            lista_permisos = self.get_permits()
            for codigo_permiso in lista_permisos:
                if not grupo.grouppermission_set.filter(permission__codename=codigo_permiso).exists():
                    messages.error(request, 'No tiene permiso para ingresar a este módulo')
                    return HttpResponseRedirect(self.get_last_url())
            if lista_permisos:
                permiso_modulo = grupo.grouppermission_set.filter(
                    permission__codename=lista_permisos[0]
                )
                if permiso_modulo.exists():
                    request.session['url_last'] = request.path
                    request.session['module'] = serializar_modulo_para_sesion(
                        permiso_modulo[0].module
                    )
            return super().get(request, *args, **kwargs)
        except Exception:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
