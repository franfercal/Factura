from crum import get_current_request
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator

from config import settings
from core.security.models import Module


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
            modules = Module.objects.filter(Q(module_type__is_active=True) | Q(module_type__isnull=True)).filter(
                groupmodule__group_id__in=[id_grupo], is_active=True, url=request.path, is_visible=True)
            if modules.exists():
                request.session['module'] = serializar_modulo_para_sesion(modules[0])
                return super().get(request, *args, **kwargs)
            else:
                messages.error(request, 'No tiene permiso para ingresar a este módulo')
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        except:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)


class PermissionMixin(object):
    permission_required = None

    def get_permits(self):
        perms = []
        if isinstance(self.permission_required, str):
            perms.append(self.permission_required)
        else:
            perms = list(self.permission_required)
        return perms

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
            permits = self.get_permits()
            for i in permits:
                if not grupo.grouppermission_set.filter(permission__codename=i).exists():
                    messages.error(request, 'No tiene permiso para ingresar a este módulo')
                    return HttpResponseRedirect(self.get_last_url())
            grouppermission = grupo.grouppermission_set.filter(permission__codename=permits[0])
            if grouppermission.exists():
                request.session['url_last'] = request.path
                request.session['module'] = serializar_modulo_para_sesion(
                    grouppermission[0].module
                )
            return super().get(request, *args, **kwargs)
        except:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
