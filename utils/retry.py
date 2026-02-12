
import time
import logging
import functools
import random

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0):
    """
    Decorator to retry a function on exception with exponential backoff.
    Especially useful for API rate limits (429).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # Check for rate limit keywords
                    error_msg = str(e).lower()
                    is_rate_limit = any(x in error_msg for x in ["429", "quota", "rate limit", "too many requests"])
                    
                    if attempt < max_retries:
                        # Add jitter to avoid thundering herd
                        sleep_time = delay * (backoff_factor ** attempt) + random.uniform(0, 0.5)
                        if is_rate_limit:
                            logger.warning(f"API rate limit (429) on {func.__name__} (attempt {attempt+1}/{max_retries+1}). Retrying in {sleep_time:.1f}s...")
                        else:
                            logger.warning(f"Error in {func.__name__}: {e}. Retrying in {sleep_time:.1f}s...")
                        time.sleep(sleep_time)
                        continue
                    
                    # If max retries hit, log error
                    logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}. Last error: {last_exception}")
                    raise last_exception
            return None # Should not reach here
        return wrapper
    return decorator
