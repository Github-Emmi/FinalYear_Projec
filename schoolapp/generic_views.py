from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.shortcuts import render

def generic_paginated_list(request, model, related_fields, template_name, table_template, base_queryset=None):
    """
    Generic paginated list view with search & AJAX support.
    base_queryset allows filtering (e.g., staff-specific quizzes).
    """
    query = request.GET.get('q', '').strip()

    # Use base_queryset if provided, else default to model.objects
    objects = base_queryset if base_queryset is not None else model.objects.all()

    if related_fields:
        objects = objects.select_related(*related_fields)

    if query:
        model_name = model.__name__

        if model_name == 'Quiz':
            objects = objects.filter(
                Q(title__icontains=query) |
                Q(subject__subject_name__icontains=query) |
                Q(class_id__class_name__icontains=query) |
                Q(session_year__session_start_year__icontains=query) |
                Q(session_year__session_end_year__icontains=query) |
                Q(department_id__department_name__icontains=query) |
                Q(staff__admin__first_name__icontains=query) |
                Q(staff__admin__last_name__icontains=query)
            )

        elif model_name == 'Subjects':
            objects = objects.filter(
                Q(subject_name__icontains=query) |
                Q(class_id__class_name__icontains=query) |
                Q(department_id__department_name__icontains=query) |
                Q(staff_id__first_name__icontains=query) |
                Q(staff_id__last_name__icontains=query)
            )

        elif model_name == 'Class':
            objects = objects.filter(Q(class_name__icontains=query))

        elif model_name == 'Departments':
            objects = objects.filter(Q(department_name__icontains=query))

        elif model_name == 'SessionYearModel':
            objects = objects.filter(
                Q(session_start_year__icontains=query) |
                Q(session_end_year__icontains=query)
            )

        else:
            objects = objects.filter(
                Q(admin__first_name__icontains=query) |
                Q(admin__last_name__icontains=query) |
                Q(admin__username__icontains=query)
            )

    paginator = Paginator(objects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'table_html': render_to_string(table_template, {'objects': page_obj}, request=request),
            'pagination_html': render_to_string('includes/pagination.html', {'page_obj': page_obj, 'search_query': query}, request=request)
        })

    return render(request, template_name, {
        'page_obj': page_obj,
        'objects': page_obj,   # <-- pass correct context name
        'search_query': query
    })
