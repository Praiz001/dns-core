"""
Custom pagination class
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Standard pagination with custom response format"""
    
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        """Return paginated response with meta information"""
        return Response({
            'success': True,
            'message': 'Data retrieved successfully',
            'data': data,
            'meta': {
                'total': self.page.paginator.count,
                'limit': self.page.paginator.per_page,
                'page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }
        })
