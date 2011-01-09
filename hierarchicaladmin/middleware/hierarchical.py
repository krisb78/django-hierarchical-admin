'''
Created on Jan 9, 2011

@author: krzysztofbandurski
'''

class HierarchicalMiddleware(object):
    
    def process_request(self, request):
        request.hierarchical_options = {}
        return None