# from django.contrib import messages
# from django.shortcuts import get_object_or_404, redirect
# from django.contrib.auth.decorators import login_required, user_passes_test
# from django.apps import apps
# from .emails import enviar_bienvenida

# Cliente = apps.get_model("cliente", "Cliente")

# def es_staff(user):
#     return user.is_authenticated and (user.is_staff or user.is_superuser)

# @login_required
# @user_passes_test(es_staff)
# def enviar_bienvenida_test(request, cliente_id: int):
#     cliente = get_object_or_404(Cliente, pk=cliente_id)
#     ok = enviar_bienvenida(
#         cliente.email,
#         cliente.nombre,
#         cliente_id=cliente.pk,
#         force=bool(request.GET.get("force"))
#     )
#     if ok:
#         messages.success(
#             request,
#             f"Correo de bienvenida enviado (o ya enviado previamente) a {cliente.email}."
#         )
#     else:
#         messages.error(
#             request,
#             f"No se pudo enviar el correo a {cliente.email}."
#         )
#     return redirect(request.META.get("HTTP_REFERER", "/"))
