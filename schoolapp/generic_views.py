from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.shortcuts import render

def generic_paginated_list(request, model, related_fields, template_name, table_template):
    query = request.GET.get('q', '').strip()
    objects = model.objects.select_related(*related_fields).all()

    if query:
        objects = objects.filter(
            Q(admin__first_name__icontains=query) |
            Q(admin__last_name__icontains=query) |
            Q(admin__username__icontains=query)
        )

    paginator = Paginator(objects, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'table_html': render_to_string(table_template, {'page_obj': page_obj}),
            'pagination_html': render_to_string('admin_templates/includes/pagination.html', {'page_obj': page_obj, 'search_query': query})
        })

    return render(request, template_name, {
        'page_obj': page_obj,
        'search_query': query
    })
