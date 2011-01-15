'''
Created on Dec 5, 2010

@author: kris
'''
class GetFormException(Exception):
    """Base class for exceptions raised in get_form."""
    def __init__(self, obj):
        self.obj = obj

class DashboardOverride(GetFormException):
    """If you want a dashboard for an object,
    raise this in get_form."""
        
class ForceDetailsReview(GetFormException):
    """Raise this in get_form if you want the user
    to review the object's details"""
