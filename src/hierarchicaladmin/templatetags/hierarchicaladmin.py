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
    for parent in parent_chain:
        href += '../'
        breadcrumbs.append( (parent, href,) )
        href += '../'
        breadcrumbs.append( (parent._meta.verbose_name_plural, href,) )
    breadcrumbs.reverse()
    
    return {
            'breadcrumbs' : breadcrumbs,
            }
    