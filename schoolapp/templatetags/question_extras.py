from django import template

register = template.Library()

@register.filter
def get_option_display(question, option):
    if option == 'A':
        return question.option_a
    elif option == 'B':
        return question.option_b
    elif option == 'C':
        return question.option_c
    elif option == 'D':
        return question.option_d
    return ''