'''
Created on Nov 20, 2010

@author: kris
'''
from django.contrib.admin.sites import AdminSite
from django.conf import settings
from django.utils.functional import update_wrapper
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.utils.translation import ugettext as _

class HierarchicalAdminSite(AdminSite):
    def __init__(self, *args, **kwargs):
        super(HierarchicalAdminSite, self).__init__(*args, **kwargs)
        self.root_admin = None
        
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url, include

        if settings.DEBUG:
            self.check_dependencies()

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        # Admin-site-wide views.
        urlpatterns = patterns('',
#            url(r'^$',
#                wrap(self.index),
#                name='index'),
            url(r'^logout/$',
                wrap(self.logout),
                name='logout'),
            url(r'^password_change/$',
                wrap(self.password_change, cacheable=True),
                name='password_change'),
            url(r'^password_change/done/$',
                wrap(self.password_change_done, cacheable=True),
                name='password_change_done'),
            url(r'^jsi18n/$',
                wrap(self.i18n_javascript, cacheable=True),
                name='jsi18n'),
            url(r'^r/(?P<content_type_id>\d+)/(?P<object_id>.+)/$',
                'django.views.defaults.shortcut'),
            (r'^', include(self.root_admin.urls)),
#            url(r'^(?P<app_label>\w+)/$',
#                wrap(self.app_index),
#                name='app_list')
        )

        # Add in each model's views.
#        for model, model_admin in self._registry.iteritems():
#            urlpatterns += patterns('',
#                url(r'^%s/' % model._meta.module_name,
#                    include(model_admin.urls))
#            )
        return urlpatterns
    
    def register(self, model_or_iterable, admin_class=None, parent_model=None, **options):
        if parent_model is not None:
            parent_admin = self._registry[parent_model]
            parent_admin.register(model_or_iterable, admin_class, **options)
            self._registry.update(parent_admin._registry)
        else:
            if self.root_admin is None:
                if not isinstance(model_or_iterable, ModelBase):
                    raise ImproperlyConfigured(_('You may not register an iterable as root!'))
                
                self.root_admin = admin_class(model_or_iterable, self)
                self._registry[model_or_iterable] = self.root_admin
            else:
                raise ImproperlyConfigured(_(u'Root admin already registered!'))
