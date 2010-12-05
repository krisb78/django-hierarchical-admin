'''
Created on Dec 5, 2010

@author: kris
'''
class DashboardOverride(Exception):
    """If you want a dashboard for an object,
    raise this in get_form."""
    def __init__(self, obj):
        self.obj = obj
