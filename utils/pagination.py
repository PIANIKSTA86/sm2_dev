from flask import request
from math import ceil

def paginate_query(query, per_page=20, page=None):
    """
    Paginate a SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        per_page: Number of items per page
        page: Current page number (from request args if not provided)
    
    Returns:
        tuple: (items, pagination_info)
    """
    if page is None:
        page = request.args.get('page', 1, type=int)
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get total count
    total = query.count()
    
    # Get items for current page
    items = query.offset(offset).limit(per_page).all()
    
    # Calculate pagination info
    total_pages = ceil(total / per_page)
    has_prev = page > 1
    has_next = page < total_pages
    prev_num = page - 1 if has_prev else None
    next_num = page + 1 if has_next else None
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_num': prev_num,
        'next_num': next_num,
        'pages': list(range(max(1, page - 2), min(total_pages + 1, page + 3)))
    }
    
    return items, pagination

def get_pagination_params():
    """Get pagination parameters from request"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Limit per_page to reasonable values
    per_page = min(max(per_page, 5), 100)
    
    return page, per_page
