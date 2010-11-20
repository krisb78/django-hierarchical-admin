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
from django.http import Http404


class HierarchicalModelAdmin(admin.ModelAdmin):
    parent_admin = None
    parent_opts = None
    index_template = 'hierarchicaladmin/index.html'
    list_view_template = 'hierarchicaladmin/list_view.html'
    change_form_template = 'hierarchicaladmin/change_form.html'
    delete_confirmation_template = 'hierarchicaladmin/delete_confirmation.html'
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
    
    def can_view_index(self, request):
        return True
            
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
            print 'added %s to urls' % model._meta.module_name
        return urlpatterns   
                
    def get_parent_chain(self, request):
        parent_id_chain = request.parent_id_chain
        if parent_id_chain:
            parent_id = parent_id_chain.pop(0)
            self.parent_admin.get_parent_chain(request)
            request.parent_chain.append(self.parent_admin.get_object(request, parent_id))
        else:
            request.parent_chain = []
        
            
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        def wrap(view):
            def wrapper(request, *args, **kwargs):
                parent_admin = self.parent_admin
                if 'extra_context' not in kwargs:
                    kwargs['extra_context'] = {}
                parent_id_chain = []
                while parent_admin is not None:
                    parent_opts = parent_admin.opts
                    parent_id = kwargs.pop('%s_id' % parent_opts.module_name)
                    parent_id_chain.append( parent_id )
                    parent_admin = parent_admin.parent_admin
                
                request.parent_id_chain = parent_id_chain
                self.get_parent_chain(request)
                
                kwargs['extra_context'].update({'parent_chain' : request.parent_chain })
                return self.admin_site.admin_view(view)(request, *args, **kwargs)
            return update_wrapper(wrapper, view)
        

        parent_admin = self.parent_admin
        parent_chain = []
        while parent_admin is not None:
            parent_chain.append(parent_admin.model._meta.module_name)
            parent_admin = parent_admin.parent_admin
            
        parent_chain.reverse()
        prefix = '_'.join(parent_chain)

        info = (prefix,
                self.model._meta.app_label, 
                self.model._meta.module_name)
            
        urlpatterns = patterns('',
            url(r'^$',
                wrap(self.changelist_view),
                name='%s_%s_%s_changelist' % info),
            url(r'^add/$',
                wrap(self.add_view),
                name='%s_%s_%s_add' % info),
            url(r'^(?P<object_id>.+)/history/$',
                wrap(self.history_view),
                name='%s_%s_%s_history' % info),
            url(r'^(?P<object_id>.+)/delete/$',
                wrap(self.delete_view),
                name='%s_%s_%s_delete' % info),
            url(r'^(?P<object_id>.+)/$',
                wrap(self.change_view),
                name='%s_%s_%s_change' % info),
        )
        return self.get_sub_urls() + urlpatterns


    def change_view(self, request, object_id, extra_context=None):
        if not self._registry:
            return super(HierarchicalModelAdmin, self).change_view(request, object_id, extra_context)
        
        """
        Displays the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """
        model = self.model
        opts = model._meta

        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        
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
            'title': u'%s' % obj,
            'original' : obj,
            'app_list': app_list,
            'root_path': self.root_path,
            'can_view_index' : self.can_view_index(request),
        }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(self.index_template or 'admin/hierarchicaladmin/index.html', context,
            context_instance=context_instance
        )

    def save_model(self, request, obj, form, change):
        parent_chain = request.parent_chain
        parent_object = (parent_chain and parent_chain[-1]) or None
        
        if not change:
            setattr(obj, self.parent_lookup, parent_object)
        
        super(HierarchicalModelAdmin, self).save_model(request, obj, form, change)