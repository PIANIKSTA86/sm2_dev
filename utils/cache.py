from app import cache
from functools import wraps
from flask import request
import hashlib

def cache_key(*args, **kwargs):
    """Generate cache key from arguments"""
    key_parts = []
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached_query(timeout=300):
    """Decorator to cache database queries"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create cache key
            key = f"query:{f.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache.set(key, result, timeout=timeout)
            return result
        
        return decorated_function
    return decorator

def invalidate_cache_pattern(pattern):
    """Invalidate cache entries matching pattern"""
    # Note: This is a simple implementation
    # In production with Redis, you'd use Redis commands for pattern deletion
    try:
        cache.clear()  # Simple approach - clear all cache
    except:
        pass

def cache_product_search(search_term, warehouse_id=None, timeout=60):
    """Cache product search results"""
    key = f"product_search:{cache_key(search_term, warehouse_id)}"
    return cache.get(key), key

def set_product_search_cache(key, results, timeout=60):
    """Set product search cache"""
    cache.set(key, results, timeout=timeout)

def cache_dashboard_stats(user_id, timeout=300):
    """Cache dashboard statistics"""
    key = f"dashboard_stats:{user_id}"
    return cache.get(key), key

def set_dashboard_stats_cache(key, stats, timeout=300):
    """Set dashboard statistics cache"""
    cache.set(key, stats, timeout=timeout)

def cache_inventory_summary(warehouse_id=None, timeout=600):
    """Cache inventory summary"""
    key = f"inventory_summary:{warehouse_id or 'all'}"
    return cache.get(key), key

def set_inventory_summary_cache(key, summary, timeout=600):
    """Set inventory summary cache"""
    cache.set(key, summary, timeout=timeout)

def clear_inventory_cache():
    """Clear all inventory-related cache"""
    try:
        # In a real implementation with Redis, you'd use pattern deletion
        cache.delete_memoized('get_dashboard_stats')
        invalidate_cache_pattern('inventory_*')
        invalidate_cache_pattern('product_search:*')
    except:
        pass

def clear_sales_cache():
    """Clear all sales-related cache"""
    try:
        invalidate_cache_pattern('dashboard_stats:*')
        invalidate_cache_pattern('sales_*')
    except:
        pass
