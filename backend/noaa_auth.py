"""
NOAA EOG Authentication Handler with OAuth Support
"""

import requests
import logging
from typing import Optional
import time
from bs4 import BeautifulSoup
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NOAAAuthenticator:
    """
    Handles authentication for NOAA EOG data access.
    Uses Keycloak OAuth-based session authentication.
    """
    
    DATA_URL_BASE = "https://eogdata.mines.edu"
    TRIGGER_URL = "https://eogdata.mines.edu/nighttime_light/monthly/v10/"
    
    def __init__(self, username: str, password: str):
        """
        Initialize authenticator.
        
        Args:
            username: NOAA EOG username/email
            password: NOAA EOG password
        """
        self.username = username
        self.password = password
        self.session = None
        self.authenticated = False
        self._authenticate()
    
    def get_authenticated_session(self) -> requests.Session:
        """
        Get an authenticated requests session.
        
        Returns:
            Authenticated requests.Session
        """
        if not self.authenticated or self.session is None:
            self._authenticate()
        
        if not self.authenticated:
            raise RuntimeError("Failed to authenticate with NOAA EOG")
        
        return self.session
    
    def _authenticate(self):
        """
        Authenticate with NOAA EOG using Keycloak OAuth flow.
        
        This implements the OAuth authorization code flow:
        1. Request protected resource (triggers redirect to login)
        2. Parse login form from Keycloak
        3. Submit credentials
        4. Handle OAuth callback and redirects
        5. Capture authenticated session cookies
        """
        try:
            logger.info("Authenticating with NOAA EOG via OAuth...")
            
            # Create new session with proper headers
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            
            # Step 1: Request protected resource (triggers OAuth redirect)
            logger.info("Step 1: Requesting protected resource...")
            response = self.session.get(self.TRIGGER_URL, allow_redirects=True)
            
            # Check if we're already authenticated (no redirect to login)
            if "eogdata.mines.edu" in response.url and "eogauth" not in response.url:
                logger.info("✅ Already authenticated (found existing session)")
                self.authenticated = True
                return
            
            # Step 2: We should now be on the Keycloak login page
            if "eogauth" not in response.url:
                # Maybe no authentication required?
                logger.warning("No OAuth redirect detected - trying without auth")
                self.authenticated = True
                return
            
            logger.info(f"Step 2: Redirected to login page: {response.url}")
            
            # Step 3: Parse the login form
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            
            if not form:
                raise ValueError("No login form found on page")
            
            action_url = form.get('action')
            if not action_url:
                raise ValueError("No form action URL found")
            
            logger.info(f"Step 3: Found login form with action: {action_url[:80]}...")
            
            # Step 4: Prepare login data
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            
            # Add all hidden fields from the form
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value', '')
                if name:
                    login_data[name] = value
                    logger.debug(f"Added hidden field: {name}")
            
            logger.info(f"Step 4: Submitting credentials for user: {self.username}")
            
            # Step 5: Submit the login form
            response = self.session.post(
                action_url,
                data=login_data,
                allow_redirects=True,
                timeout=30
            )
            
            # Step 6: Verify we're back on the data site (successful authentication)
            final_url = response.url
            logger.info(f"Step 5: Final URL after login: {final_url}")
            
            if "eogdata.mines.edu" in final_url and "eogauth" not in final_url:
                self.authenticated = True
                logger.info("✅ Successfully authenticated with NOAA EOG!")
                
                # Log session cookies (masked)
                cookie_count = len(self.session.cookies)
                logger.info(f"Session has {cookie_count} cookies")
                
            elif "error" in final_url.lower() or "login" in final_url.lower():
                # Still on login page or error page
                logger.error("❌ Authentication failed - still on login/error page")
                logger.error(f"Final URL: {final_url}")
                
                # Try to extract error message
                soup = BeautifulSoup(response.text, 'html.parser')
                error_div = soup.find('div', class_='alert-error') or soup.find('span', class_='kc-feedback-text')
                if error_div:
                    error_msg = error_div.get_text(strip=True)
                    logger.error(f"Error message: {error_msg}")
                
                self.authenticated = False
            else:
                logger.warning(f"⚠️ Unexpected redirect: {final_url}")
                # Try to continue anyway
                self.authenticated = True
                
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.authenticated = False
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self.authenticated
    
    def test_access(self, test_url: str = None) -> bool:
        """
        Test if authenticated session can access protected resources.
        
        Args:
            test_url: URL to test (defaults to a data directory)
            
        Returns:
            True if access successful
        """
        if not self.authenticated:
            return False
        
        if test_url is None:
            test_url = f"{self.DATA_URL_BASE}/nighttime_light/monthly/v10/2024/"
        
        try:
            response = self.session.get(test_url, timeout=10)
            
            # Should get directory listing, not login page
            is_logged_in = (
                response.status_code == 200 and
                "login" not in response.text.lower()[:500] and
                "eogauth" not in response.url
            )
            
            if is_logged_in:
                logger.info(f"✅ Access test passed: {test_url}")
            else:
                logger.warning(f"⚠️ Access test failed: Got login page")
                
            return is_logged_in
            
        except Exception as e:
            logger.error(f"Access test error: {e}")
            return False

