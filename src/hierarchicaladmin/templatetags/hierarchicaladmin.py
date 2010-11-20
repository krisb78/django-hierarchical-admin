'''
Created on Nov 20, 2010

@author: kris
'''
from django import template

register = template.Library()

@register.inclusion_tag('hierarchicaladmin/breadcrumbs.html')
def hierarchical_breadcrumbs(parent_chain, upinit=''):
    parents = list(parent_chain)
    parents.reverse()
    breadcrumbs = []
    href = upinit
    
    for parent in parents:
        href += '../'
        parent_obj_breadcrumb = parent, href
        href += '../'
        parent_list_breadcrumb = parent._meta.verbose_name_plural, href
        breadcrumbs.append( parent_obj_breadcrumb )
        breadcrumbs.append( parent_list_breadcrumb )
    
    breadcrumbs.reverse()
    
    return {
            'breadcrumbs' : breadcrumbs,
            }
    