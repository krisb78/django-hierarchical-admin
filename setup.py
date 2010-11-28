'''
Created on Nov 7, 2010

@author: kris
'''
from setuptools import setup, find_packages
#import os
import hierarchicaladmin

setup(
    name='hierarchicaladmin',
    author="Krzysztof Bandurski",
    author_email="krzysztof.bandurski@gmail.com",
    version=hierarchicaladmin.__version__,
    description='A hierarchical admin class for Django',
#    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
#    url='http://www.django-cms.org/',
    license='BSD License',
    platforms=['OS Independent'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    requires=[
        'django (>1.2.0)',
    ],
    packages=find_packages(exclude=["example", "example.*"]),
    include_package_data=True,
    zip_safe = False
)
