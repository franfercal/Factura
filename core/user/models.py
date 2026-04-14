import uuid

from crum import get_current_request
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, UserManager
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone

from config import settings


class User(AbstractBaseUser, PermissionsMixin):
    names = models.CharField(max_length=150, null=True, blank=True, verbose_name='Nombres')
    username = models.CharField(max_length=150, unique=True, verbose_name='Username')
    dni = models.CharField(max_length=10, unique=True, verbose_name='Número de cedula')
    image = models.ImageField(upload_to='users/%Y/%m/%d', null=True, blank=True, verbose_name='Imagen')
    email = models.EmailField(null=True, blank=True, verbose_name='Correo electrónico')
    is_active = models.BooleanField(default=True, verbose_name='Estado')
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    is_change_password = models.BooleanField(default=False)
    email_reset_token = models.TextField(null=True, blank=True)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def toJSON(self):
        item = model_to_dict(self, exclude=['last_login', 'email_reset_token', 'password', 'user_permissions'])
        item['image'] = self.get_image()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['groups'] = [{'id': i.id, 'name': i.name} for i in self.groups.all()]
        item['last_login'] = None if self.last_login is None else self.last_login.strftime('%Y-%m-%d')
        return item

    def get_full_name(self):
        return f'{self.names} ({self.dni})'

    def generate_token(self):
        return str(uuid.uuid4())

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_group_id_session(self):
        try:
            solicitud = get_current_request()
            grupo_en_sesion = solicitud.session.get('group')
            if grupo_en_sesion is None:
                return 0
            # Con JSONSerializer solo podemos guardar datos JSON-serializables.
            # El grupo se almacena como dict {'id', 'name'} (ver set_group_session).
            if isinstance(grupo_en_sesion, dict):
                return int(grupo_en_sesion['id'])
            # Compatibilidad defensiva si en memoria hubiera un objeto antiguo.
            return int(grupo_en_sesion.id)
        except Exception:
            return 0

    def set_group_session(self):
        """
        Asigna el perfil (grupo Django) activo en sesión.

        Antes solo se escribía si la clave 'group' no existía; si existía con
        valor None (p. ej. tras UserChooseProfileView sin coincidencias) o con
        datos inválidos, el dashboard quedaba vacío y las plantillas fallaban
        al resolver request.session.group.id.
        """
        try:
            solicitud = get_current_request()
            grupos = list(solicitud.user.groups.all())
            if not grupos:
                return
            grupo_actual = solicitud.session.get('group')
            # Reparar: ausente, None, dict incompleto o formato heredado no dict.
            debe_asignar_grupo = (
                not isinstance(grupo_actual, dict)
                or grupo_actual.get('id') is None
            )
            if debe_asignar_grupo:
                primer_grupo = grupos[0]
                solicitud.session['group'] = {
                    'id': primer_grupo.id,
                    'name': primer_grupo.name,
                }
        except Exception:
            pass

    def create_or_update_password(self, password):
        if self.pk is None:
            self.set_password(password)
        else:
            user = User.objects.get(pk=self.pk)
            if user.password != password:
                self.set_password(password)

    def get_short_name(self):
        if self.names is not None:
            names = self.names.split(' ')
            if len(names) > 1:
                return f'{names[0]} {names[1]}'
        return self.names

    def __str__(self):
        return self.names

    def is_client(self):
        return hasattr(self, 'client')

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-id']
