from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class CustomAuthBackend(ModelBackend):
    """
    Permite autenticar usuarios aunque estén inactivos,
    para poder diferenciar el mensaje de error.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password):
            # Devolvemos siempre el usuario (activo o inactivo)
            return user
        return None
