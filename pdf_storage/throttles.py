# config/throttles.py

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle


class LoginThrottle(AnonRateThrottle):
    """
    Custom throttle for login endpoint.
    Uses IP address to identify clients (not user ID)
    because user is not logged in yet when logging in.
    
    scope = 'login' tells DRF to look up 'login' key
    in DEFAULT_THROTTLE_RATES
    """
    scope = 'login'


class UploadThrottle(ScopedRateThrottle):
    """
    Custom throttle for upload endpoint.
    Uses user ID to identify clients.
    scope = 'upload' tells DRF to look up 'upload' key
    """
    scope = 'upload'

class PdfThrottle(ScopedRateThrottle):
    """
    Custom throttle for PDF upload endpoint.
    Uses user ID to identify clients.
    scope = 'pdfs' tells DRF to look up 'pdfs' key
    """
    scope = 'pdfs'