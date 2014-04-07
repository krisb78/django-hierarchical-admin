'''
Created on Nov 20, 2010

@author: kris
'''
from django.contrib import admin
from django.utils.functional import update_wrapper
from django.contrib.admin.util import unquote
from django.conf import settings
from django.db.models.base import ModelBase
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.views.decorators.cache import never_cache
from django.shortcuts import render_to_response
from django import http, template
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.utils.html import escape
from django.utils.encoding import force_unicode
from django.http import Http404, HttpResponseRedirect

from hierarchicaladmin.exceptions import DashboardOverride, ForceDetailsReview

class DashboardAdmin(admin.ModelAdmin):
    dashboard_template = None
    dashboard_template_file = 'dashboard.html'
    change_form_template = 'dashboardadmin/change_form.html'
    edit_details = True
    
    def get_object_to_change(self, request, object_id):
        """Helper method for getting an object and checking
        permissions to change."""
        model = self.model
        opts = model._meta

        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})    
        return obj
    
    def show_dashboard(self, request, obj):
        return True
    
    def can_edit_details(self, request, obj):
        # By default, if a user has the change permission
        # and dashboard is to be shown,
        # the user can also edit details.
        # Override this if a different behaviour is required.
        return self.edit_details \
               and self.show_dashboard(request, obj) \
               and self.has_change_permission(request, obj)

    def has_add_permission(self, request):
        # This is here to make the 'save and add another' button
        # disappear from the edit details page        
        edit_details = request.hierarchical_options.get('edit_details', False)
        if edit_details:
            return False
        
        return super(DashboardAdmin, 
                     self).has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # This is here to make the 'delete' link 
        # disappear from the edit details page        
        edit_details = request.hierarchical_options.get('edit_details', False)
        if edit_details:
            return False
        
        return super(DashboardAdmin,
                     self).has_delete_permission(request, obj)
                         
    def change_view(self, request, object_id, extra_context=None):
        
        # Try to return the default chante view. If a DashboardOverride is caught,
        # return dashboard_view        
        try:
            return super(DashboardAdmin, self).change_view(request, object_id, extra_context=extra_context)
        except DashboardOverride, e:
            return self.dashboard_view(request, e.obj, extra_context)
        except ForceDetailsReview, e:
            return HttpResponseRedirect('edit_details/')

    def force_details_review(self, request, obj):
        """Override this to force user to review details of the object.
        If you want to display a message explaining why the user
        was forced to edit the object's details, override change_form
        and add a message just before returning the form.
        """
        return False

    def get_form(self, request, obj=None, **kwargs):
        # Get the edit details flag from the request
        # (this could be set by edit_details_view)
        edit_details = request.hierarchical_options.get('edit_details', False)
        can_edit_details = self.can_edit_details(request, obj)
        
        # If someone tries to edit details when not allowed,
        # raise Http404        
        if edit_details and not can_edit_details:
            raise Http404
        
        # Check if the user is allowed to edit details
        edit_details = obj and edit_details and can_edit_details
        
        force_details_review = can_edit_details and self.force_details_review(request, obj)         
        
        # If we have an object and a dasboard is to be shown,
        # raise a DashboardOverride exception, passing the obj
        # to the constructor        
        if obj and self.show_dashboard(request, obj) and not edit_details:
            if force_details_review:
                raise ForceDetailsReview(obj)
            raise DashboardOverride(obj)
                
        # Otherwise just return the form, but first check if there is 
        # nothing that has to be done with the object.
        return super(DashboardAdmin, self).get_form(request, obj, **kwargs)
        
    def edit_details_view(self, request, object_id, extra_context=None):
        request.hierarchical_options['edit_details'] = True
        context = {'edit_details' : True,
                   'title': _(u'Edit details')}
        context.update(extra_context or {})
        return self.change_view(request, object_id, extra_context=context)
    
    def dashboard_view(self, request, obj, extra_context=None):        
        """
        Displays the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """        
        model = self.model
        opts = model._meta

        context = {
            'title': u'%s' % obj,
            'original' : obj,
            'opts' : obj._meta,
            'app_label': opts.app_label,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'can_edit_details' : self.can_edit_details(request, obj),
        }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        dashboard_template_file = self.dashboard_template_file
        return render_to_response(self.dashboard_template or [ 
            "admin/%s/%s/%s" % (app_label, opts.object_name.lower(), dashboard_template_file),
            "admin/%s/%s" % (app_label, dashboard_template_file),
            "admin/%s" % dashboard_template_file],                                  
            context,
            context_instance=context_instance
        )
        
    def wrap_view(self, view):
        def wrapper(request, *args, **kwargs):
            return self.admin_site.admin_view(view)(request, *args, **kwargs)
        return update_wrapper(wrapper, view)

    def get_prefix(self):
        return ''

    def get_info(self):
        prefix = self.get_prefix()
        info = (prefix,
                self.model._meta.app_label, 
                self.model._meta.module_name)
        return info

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        info = self.get_info()
            
        urlpatterns = patterns('',
            url(r'^$',
                self.wrap_view(self.changelist_view),
                name='%s%s_%s_changelist' % info),
            url(r'^add/$',
                self.wrap_view(self.add_view),
                name='%s%s_%s_add' % info),
            url(r'^(?P<object_id>.+)/edit_details/$',
                self.wrap_view(self.edit_details_view),
                name='%s%s_%s_edit_details' % info),
            url(r'^(?P<object_id>.+)/history/$',
                self.wrap_view(self.history_view),
                name='%s%s_%s_history' % info),
            url(r'^(?P<object_id>.+)/delete/$',
                self.wrap_view(self.delete_view),
                name='%s%s_%s_delete' % info),
            url(r'^(?P<object_id>.+)/$',
                self.wrap_view(self.change_view),
                name='%s%s_%s_change' % info),
        )
        return urlpatterns


class HierarchicalModelAdmin(DashboardAdmin):
    
    dashboard_template_file = 'hierarchical_dashboard.html'
    
    parent_admin = None
    parent_opts = None
    change_list_template = 'hierarchicaladmin/change_list.html'
    change_form_template = 'hierarchicaladmin/change_form.html'
    delete_confirmation_template = 'hierarchicaladmin/delete_confirmation.html'
    delete_selected_confirmation_template = 'hierarchicaladmin/delete_selected_confirmation.html'
    object_history_template = 'hierarchicaladmin/object_history.html'
    
    def __init__(self, *args, **kwargs):
        super(HierarchicalModelAdmin, self).__init__(*args, **kwargs)
        if self.parent_admin is not None:
            self.parent_opts = self.parent_admin.model._meta
            parent_exclude = [self.parent_lookup]
            if self.exclude is not None:
                self.exclude = [e for e in self.exclude] + parent_exclude
            else:
                self.exclude = parent_exclude
                
                
        self._registry = {}
        self.root_path = None

    @property
    def parent_lookup(self):
        return '%s' % self.parent_opts.module_name
    
#    def can_view_index(self, request):
#        return True
            
    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Registers the given model(s) with this Admin class.
        
        The model(s) should be Model classes, not instances.

        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.
        """
        if not admin_class:
            admin_class = HierarchicalModelAdmin
        elif not issubclass(admin_class, HierarchicalModelAdmin):
            raise ImproperlyConfigured('You may only register HierarchicalAdmin subclasses'
                                       'with InstitutionAdmin!')

        # Don't import the humongous validation code unless required
        if admin_class and settings.DEBUG:
            from django.contrib.admin.validation import validate
        else:
            validate = lambda model, adminclass: None

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)

            # If we got **options then dynamically construct a subclass of
            # admin_class with those **options.
            attrs = {}
            attrs['__module__'] = __name__
            attrs['parent_admin'] = self
            attrs.update(options or {})
#            if options:
#                # For reasons I don't quite understand, without a __module__
#                # the created class appears to "live" in the wrong place,
#                # which causes issues later on.
#                options['__module__'] = __name__
                
            admin_class = type("%sHierarchicalAdmin" % model.__name__, (admin_class,), attrs)

            # Validate (which might be a no-op)
            validate(admin_class, model)

            # Instantiate the admin class to save in the registry
            self._registry[model] = admin_class(model, self.admin_site)
        

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]
        
    def queryset(self, request):
        qs = super(HierarchicalModelAdmin, self).queryset(request)
        if request.parent_chain:
            parent = request.parent_chain[-1]
            qs = qs.filter(**{'%s' % self.parent_lookup : parent})
        return qs
    
    def get_sub_urls(self):
        from django.conf.urls.defaults import patterns, url, include
        
        urlpatterns = patterns('',)
        for model, model_admin in self._registry.iteritems():
            urlpatterns += patterns('',
                url(r'^(?P<%s_id>.+)/%s/' % (self.model._meta.module_name,
                                             model._meta.module_name),
                    include(model_admin.urls))
            )
            
        return urlpatterns   
                
    def get_parent_chain(self, request):
        parent_id_chain = request.parent_id_chain
        if parent_id_chain:
            parent_id = parent_id_chain.pop(0)
            self.parent_admin.get_parent_chain(request)
            request.parent_chain.append(self.parent_admin.get_object(request, parent_id))
        else:
            request.parent_chain = []
            
    def get_parent_obj(self, request):
        parent_chain = request.parent_chain
        parent_obj = (parent_chain and parent_chain[-1]) or None        
        return parent_obj

    def wrap_view(self, view):
        def wrapper(request, *args, **kwargs):
            parent_admin = self.parent_admin
            parent_id_chain = []
            while parent_admin is not None:
                parent_opts = parent_admin.opts
                parent_id = kwargs.pop('%s_id' % parent_opts.module_name)
                parent_id_chain.append( parent_id )
                parent_admin = parent_admin.parent_admin
            
            request.parent_id_chain = parent_id_chain
            self.get_parent_chain(request)
                            
            return self.admin_site.admin_view(view)(request, *args, **kwargs)
        return update_wrapper(wrapper, view)

    def get_prefix(self):
        parent_admin = self.parent_admin
        parent_chain = []
        while parent_admin is not None:
            parent_chain.append(parent_admin.model._meta.module_name)
            parent_admin = parent_admin.parent_admin
            
        parent_chain.reverse()
        prefix = '_'.join(parent_chain)
        if prefix:
            prefix += '_'
        return prefix
            
    def get_urls(self):
        # Just need to add sub_urls here...
        urls = super(HierarchicalModelAdmin, self).get_urls()
        return self.get_sub_urls() + urls


    def show_dashboard(self, request, obj):
        """Determines if a dashboard is to be shown in change view,
        instead of the default form. Dashboard is shown by default
        if the current admin has any children"""
        return self._registry
    
    def get_form(self, request, obj=None, **kwargs):
                        
        form = super(HierarchicalModelAdmin, self).get_form(request, obj, **kwargs)
        
        # Store parent chain in form, might be useful
        # for validation
        form._parent_chain = request.parent_chain
        form._model_admin = self
        return form

    def dashboard_view(self, request, obj, extra_context=None):
        model = self.model
        opts = model._meta
        app_dict = {}
        user = request.user
        for model, model_admin in self._registry.items():
            app_label = model._meta.app_label
            has_module_perms = user.has_module_perms(app_label)

            if has_module_perms:
                perms = model_admin.get_model_perms(request)

                # Check whether user has any perm for this module.
                # If so, add the module to the model_list.
                if True in perms.values():
                    model_dict = {
                        'name': capfirst(model._meta.verbose_name_plural),
                        'admin_url': mark_safe('%s/' % (model.__name__.lower())),
                        'perms': perms,
                    }
                    if app_label in app_dict:
                        app_dict[app_label]['models'].append(model_dict)
                    else:
                        app_dict[app_label] = {
                            'name': app_label.title(),
                            'app_url': app_label + '/',
                            'has_module_perms': has_module_perms,
                            'models': [model_dict],
                        }

        # Sort the apps alphabetically.
        app_list = app_dict.values()
        app_list.sort(key=lambda x: x['name'])

        # Sort the models alphabetically within each app.
        for app in app_list:
            app['models'].sort(key=lambda x: x['name'])
            
        context = {
            'app_list': app_list,                   
            'root_path': self.root_path,
        }
        context.update(extra_context or {})
        return super(HierarchicalModelAdmin, 
                     self).dashboard_view(request, obj, extra_context=context)
    
    def link_to_parent(self, request, obj, parent_obj, form):
        setattr(obj, self.parent_lookup, parent_obj)

    def save_form(self, request, form, change):
        obj = super(HierarchicalModelAdmin,
                    self).save_form(request, form, change)
        
        parent_obj = self.get_parent_obj(request)
        
        if not change and parent_obj:
            self.link_to_parent(request, obj, parent_obj, form)
        
        return obj
    
#    def save_model(self, request, obj, form, change):
#        
#        parent_obj = self.get_parent_obj(request)
#        
#        if not change and parent_obj:
#            self.link_to_parent(request, obj, parent_obj, form)
#        
#        super(HierarchicalModelAdmin, self).save_model(request, obj, form, change)
