"""
Unit tests for Environment Tracking Service
"""
import pytest
from unittest.mock import Mock, MagicMock
from fastapi import Request

from backend.services.audit.environment_tracker import EnvironmentTracker, environment_tracker


class TestEnvironmentTracker:
    """Test cases for EnvironmentTracker"""
    
    def test_get_system_info(self):
        """Test system information capture"""
        system_info = EnvironmentTracker._get_system_info()
        
        assert "platform" in system_info
        assert "architecture" in system_info
        assert "python_version" in system_info
        assert system_info["python_implementation"] is not None
    
    def test_get_application_info(self):
        """Test application information capture"""
        app_info = EnvironmentTracker._get_application_info()
        
        assert "version" in app_info
        assert "environment" in app_info
        assert "process_id" in app_info
        assert isinstance(app_info["process_id"], int)
    
    def test_capture_environment_without_request(self):
        """Test environment capture without HTTP request"""
        env_data = EnvironmentTracker.capture_environment(request=None)
        
        assert "captured_at" in env_data
        assert "system" in env_data
        assert "application" in env_data
        assert "http" not in env_data  # Should not be present without request
    
    def test_capture_environment_with_request(self):
        """Test environment capture with HTTP request"""
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/sar/generate"
        mock_request.url.__str__ = Mock(return_value="http://localhost/api/v1/sar/generate")
        mock_request.query_params = {}
        mock_request.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "accept-language": "en-US,en;q=0.9",
        }
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.100"
        mock_request.client.port = 54321
        
        env_data = EnvironmentTracker.capture_environment(request=mock_request)
        
        assert "http" in env_data
        assert "client" in env_data
        assert env_data["http"]["method"] == "POST"
        assert env_data["http"]["path"] == "/api/v1/sar/generate"
        assert env_data["client"]["user_agent"] is not None
    
    def test_parse_user_agent_chrome(self):
        """Test Chrome user agent parsing"""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        
        result = EnvironmentTracker._parse_user_agent(ua)
        
        assert result["browser"] == "Chrome"
        assert result["os"] == "Windows"
        assert result["device_type"] == "desktop"
    
    def test_parse_user_agent_firefox(self):
        """Test Firefox user agent parsing"""
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
        
        result = EnvironmentTracker._parse_user_agent(ua)
        
        assert result["browser"] == "Firefox"
        assert result["os"] == "macOS"
    
    def test_parse_user_agent_mobile(self):
        """Test mobile user agent parsing"""
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Mobile/15E148"
        
        result = EnvironmentTracker._parse_user_agent(ua)
        
        assert result["os"] == "iOS"
        assert result["device_type"] == "mobile"
    
    def test_extract_key_environment_fields(self):
        """Test extraction of key fields from environment data"""
        env_data = {
            "client": {
                "browser": "Chrome",
                "browser_version": "120.0.0.0",
                "os": "Windows",
                "device_type": "desktop",
                "screen_resolution": "1920x1080",
                "timezone": "America/New_York",
            },
            "application": {
                "version": "1.0.0",
            }
        }
        
        fields = EnvironmentTracker.extract_key_environment_fields(env_data)
        
        assert fields["browser_info"] == "Chrome 120.0.0.0"
        assert fields["os_info"] == "Windows"
        assert fields["device_type"] == "desktop"
        assert fields["screen_resolution"] == "1920x1080"
        assert fields["timezone"] == "America/New_York"
        assert fields["application_version"] == "1.0.0"
    
    def test_sanitize_environment_data(self):
        """Test sanitization of sensitive environment data"""
        env_data = {
            "http": {
                "headers": {
                    "authorization": "Bearer secret-token",
                    "cookie": "session=abc123",
                    "user-agent": "Chrome/120",
                }
            }
        }
        
        sanitized = EnvironmentTracker.sanitize_environment_data(env_data)
        
        assert sanitized["http"]["headers"]["authorization"] == "[REDACTED]"
        assert sanitized["http"]["headers"]["cookie"] == "[REDACTED]"
        assert sanitized["http"]["headers"]["user-agent"] == "Chrome/120"
    
    def test_singleton_instance(self):
        """Test that environment_tracker is a singleton"""
        assert environment_tracker is not None
        assert isinstance(environment_tracker, EnvironmentTracker)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
