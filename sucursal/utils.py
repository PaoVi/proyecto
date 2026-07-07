def sucursal_filter(queryset, request, field='sucursal'):
    sucursal = getattr(request, 'sucursal', None)
    if sucursal:
        return queryset.filter(**{field: sucursal})
    return queryset


def sucursal_save(instance, request, field='sucursal'):
    sucursal = getattr(request, 'sucursal', None)
    if sucursal and not getattr(instance, field + '_id', None):
        setattr(instance, field, sucursal)
    return instance
