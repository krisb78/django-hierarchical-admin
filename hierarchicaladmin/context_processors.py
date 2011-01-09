'''
Created on Jan 9, 2011

@author: krzysztofbandurski
'''

def hierarchical(request):
    return {
        'hierarchical_options': request.hierarchical_options,
    }