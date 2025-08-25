########### schoolapp/generic_views.py
from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.shortcuts import render

def generic_paginated_list(
    request,
    model,
    related_fields,
    template_name,
    table_template,
    base_qs=None,
    per_page=10,
    extra_context=None,
):
    query = (request.GET.get('q') or '').strip()

    # 🚩 Use staff-filtered base_qs when provided
    if base_qs is not None:
        objects = base_qs.select_related(*related_fields)
    else:
        objects = model.objects.select_related(*related_fields).all()


    if query:
        model_name = model.__name__
        if model_name == 'Quiz':
            objects = objects.filter(
                Q(title__icontains=query) |
                Q(subject__subject_name__icontains=query) |
                Q(class_id__class_name__icontains=query) |
                Q(session_year__session_name__icontains=query) |
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
            objects = objects.filter(
                Q(class_name__icontains=query)
                 
            )

        elif model_name == 'Departments':
            objects = objects.filter(
                Q(department_name__icontains=query)
                 
            )

        elif model_name == 'SessionYearModel':
            objects = objects.filter(
                Q(session_name__icontains=query) |
                Q(session_start_year__icontains=query) |
                Q(session_end_year__icontains=query)
            )
        
        if hasattr(model, 'created_at'):
            objects = objects.order_by('-created_at', '-id')

        else:
            # Default filtering for models with 'admin' relation
            objects = objects.filter(
                Q(admin__first_name__icontains=query) |
                Q(admin__last_name__icontains=query) |
                Q(admin__username__icontains=query)
            )

    paginator = Paginator(objects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # AJAX return partials
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        table_html = render_to_string(table_template, {"objects": page_obj}, request=request)
        pagination_html = render_to_string("includes/pagination.html", {"page_obj": page_obj}, request=request)
        return JsonResponse({"table_html": table_html, "pagination_html": pagination_html})

    ctx = {"objects": page_obj, "page_obj": page_obj, "search_query": query}
    if extra_context:
        ctx.update(extra_context)
    return render(request, template_name, ctx)