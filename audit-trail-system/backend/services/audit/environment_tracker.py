"""
Environment Tracker Service

Captures comprehensive environment and system context for audit trail.
This is critical for regulatory compliance and investigation purposes.
"""
from typing import Dict, Optional, Any
from datetime import datetime
from fastapi import Request
import platform
import sys
import os


class EnvironmentTracker:
    """
    Service to capture and track environment context for audit purposes.
    
    Captures:
    - User agent and browser information
    - Operating system details
    - Device information
    - Network information
    - Application context
    - Timestamp and timezone information
    """
    
    @staticmethod
    def capture_environment(request: Optional[Request] = None) -> Dict[str, Any]:
        """
        Capture comprehensive environment information
        
        Args:
            request: FastAPI request object (optional)
            
        Returns:
            Dict containing environment context
        """
        env_data = {
            "captured_at": datetime.utcnow().isoformat(),
            "system": EnvironmentTracker._get_system_info(),
            "application": EnvironmentTracker._get_application_info(),
        }
        
        if request:
            env_data.update({
                "http": EnvironmentTracker._get_http_info(request),
                "client": EnvironmentTracker._get_client_info(request),
            })
        
        return env_data
    
    @staticmethod
    def _get_system_info() -> Dict[str, str]:
        """Get system-level information"""
        return {
            "platform": platform.platform(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
        }
    
    @staticmethod
    def _get_application_info() -> Dict[str, Any]:
        """Get application-level information"""
        return {
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "production"),
            "deployment_id": os.getenv("DEPLOYMENT_ID"),
            "server_name": os.getenv("SERVER_NAME", platform.node()),
            "process_id": os.getpid(),
        }
    
    @staticmethod
    def _get_http_info(request: Request) -> Dict[str, Any]:
        """Get HTTP request information"""
        return {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_host": request.client.host if request.client else None,
            "client_port": request.client.port if request.client else None,
        }
    
    @staticmethod
    def _get_client_info(request: Request) -> Dict[str, Optional[str]]:
        """Get client-side information from request headers"""
        headers = request.headers
        
        user_agent = headers.get("user-agent", "")
        
        # Parse basic browser info
        browser_info = EnvironmentTracker._parse_user_agent(user_agent)
        
        return {
            "user_agent": user_agent,
            "browser": browser_info.get("browser"),
            "browser_version": browser_info.get("version"),
            "os": browser_info.get("os"),
            "device_type": browser_info.get("device_type"),
            "accept_language": headers.get("accept-language"),
            "accept_encoding": headers.get("accept-encoding"),
            "timezone": headers.get("x-timezone"),  # Custom header
            "screen_resolution": headers.get("x-screen-resolution"),  # Custom header
            "referrer": headers.get("referer"),
            "origin": headers.get("origin"),
        }
    
    @staticmethod
    def _parse_user_agent(user_agent: str) -> Dict[str, Optional[str]]:
        """
        Parse user agent string to extract browser and OS info
        
        This is a simplified parser. For production, consider using
        a library like user-agents or httpagentparser.
        """
        ua_lower = user_agent.lower()
        
        # Detect browser
        browser = None
        version = None
        
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser = "Chrome"
            if "chrome/" in ua_lower:
                version = ua_lower.split("chrome/")[1].split()[0]
        elif "edg" in ua_lower:
            browser = "Edge"
            if "edg/" in ua_lower:
                version = ua_lower.split("edg/")[1].split()[0]
        elif "firefox" in ua_lower:
            browser = "Firefox"
            if "firefox/" in ua_lower:
                version = ua_lower.split("firefox/")[1].split()[0]
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "Safari"
            if "version/" in ua_lower:
                version = ua_lower.split("version/")[1].split()[0]
        
        # Detect OS
        os_name = None

    # Mobile first
        if "iphone" in ua_lower or "ipad" in ua_lower:
            os_name = "iOS"
        elif "android" in ua_lower:
            os_name = "Android"

        # Desktop next
        elif "windows" in ua_lower:
            os_name = "Windows"
        elif "mac os x" in ua_lower or "macos" in ua_lower:
            os_name = "macOS"
        elif "linux" in ua_lower:
            os_name = "Linux"
        else:
            os_name = "Unknown"

        
        # Detect device type
        device_type = "desktop"
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device_type = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_type = "tablet"
        
        return {
            "browser": browser,
            "version": version,
            "os": os_name,
            "device_type": device_type,
        }
    
    @staticmethod
    def extract_key_environment_fields(env_data: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Extract key environment fields for database columns
        
        Args:
            env_data: Full environment data dictionary
            
        Returns:
            Dict with extracted key fields
        """
        client = env_data.get("client", {})
        
        browser_info = None
        if client.get("browser"):
            browser_info = f"{client.get('browser')} {client.get('browser_version', '')}".strip()
        
        return {
            "browser_info": browser_info,
            "os_info": client.get("os"),
            "device_type": client.get("device_type"),
            "screen_resolution": client.get("screen_resolution"),
            "timezone": client.get("timezone"),
            "application_version": env_data.get("application", {}).get("version"),
        }
    
    @staticmethod
    def sanitize_environment_data(env_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize environment data by removing sensitive information
        
        Args:
            env_data: Full environment data
            
        Returns:
            Sanitized environment data
        """
        sanitized = env_data.copy()
        
        # Remove sensitive headers
        if "http" in sanitized and "headers" in sanitized["http"]:
            headers = sanitized["http"]["headers"]
            sensitive_headers = [
                "authorization",
                "cookie",
                "x-api-key",
                "x-auth-token",
            ]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[REDACTED]"
        
        return sanitized


# Singleton instance
environment_tracker = EnvironmentTracker()
