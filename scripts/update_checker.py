#!/usr/bin/env python3
"""
Energy Manager Update Checker v0.2.4
"""

import os
import json
import urllib.request
import urllib.error
import hashlib
import ssl
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

class EnergyManagerUpdateChecker:
    def __init__(self, config_dir: str = "/config", server_url: str = "https://updates.energymanager.com.au", verify_ssl: bool = True):
        self.config_dir = config_dir
        self.server_url = server_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.em_dir = os.path.join(config_dir, ".energy_manager")
        self.version_file = os.path.join(self.em_dir, "version.txt")
        self.checksums_file = os.path.join(self.em_dir, "checksums.json")
        
        os.makedirs(self.em_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.em_dir, 'update_checker.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _make_http_request(self, url: str) -> Dict:
        try:
            req = urllib.request.Request(url)
            
            if not self.verify_ssl and url.startswith('https://'):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                    return {
                        'success': True,
                        'status_code': response.status,
                        'content': response.read().decode('utf-8')
                    }
            else:
                with urllib.request.urlopen(req, timeout=30) as response:
                    return {
                        'success': True,
                        'status_code': response.status,
                        'content': response.read().decode('utf-8')
                    }
        except urllib.error.HTTPError as e:
            return {
                'success': False,
                'status_code': e.code,
                'error': f"HTTP {e.code}: {e.reason}"
            }
        except Exception as e:
            return {
                'success': False,
                'status_code': 0,
                'error': str(e)
            }

    def get_current_version(self) -> str:
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            self.logger.warning(f"Could not read version file: {e}")
        return "0.0.1"

    def set_current_version(self, version: str):
        with open(self.version_file, 'w') as f:
            f.write(version)

    def get_remote_version(self) -> Optional[str]:
        try:
            url = f"{self.server_url}/version.txt"
            self.logger.info(f"Checking for remote version at: {url}")
            
            result = self._make_http_request(url)
            if result['success']:
                version = result['content'].strip()
                self.logger.info(f"Remote version found: {version}")
                return version
            else:
                self.logger.error(f"Failed to check remote version: {result.get('error')}")
                self.logger.error(f"Status code: {result.get('status_code')}")
                self.logger.error(f"URL attempted: {url}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to check remote version: {e}")
            return None

    def check_for_updates_force(self) -> Dict:
        current_version = self.get_current_version()
        remote_version = self.get_remote_version()
        
        result = {
            'current_version': current_version,
            'remote_version': remote_version,
            'update_available': True,  # Always True for force mode
            'manifest': None
        }
        
        # Always download manifest in force mode
        if remote_version:
            result['manifest'] = self.get_update_manifest()
        
        return result

    def get_update_manifest(self) -> Optional[Dict]:
        try:
            url = f"{self.server_url}/manifest.json"
            self.logger.info(f"Downloading manifest from: {url}")
            
            result = self._make_http_request(url)
            if result['success']:
                manifest = json.loads(result['content'])
                self.logger.info(f"Manifest downloaded successfully, version: {manifest.get('version', 'unknown')}")
                return manifest
            else:
                self.logger.error(f"Failed to download manifest: {result.get('error')}")
                self.logger.error(f"Status code: {result.get('status_code')}")
                self.logger.error(f"URL attempted: {url}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to download manifest: {e}")
            return None

    def download_file(self, remote_path: str, local_path: str) -> bool:
        try:
            url = f"{self.server_url}/files/{remote_path}"
            result = self._make_http_request(url)
            
            if result['success']:
                # Ensure directory exists
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(result['content'])
                
                self.logger.info(f"Downloaded {remote_path} to {local_path}")
                return True
            else:
                self.logger.error(f"Failed to download {remote_path}: {result.get('error')}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to download {remote_path}: {e}")
            return False

    def verify_file_checksum(self, filepath: str, expected_checksum: str) -> bool:
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            actual_checksum = hash_md5.hexdigest()
            return actual_checksum == expected_checksum
        except Exception as e:
            self.logger.error(f"Failed to verify checksum for {filepath}: {e}")
            return False

    def check_for_updates(self) -> Dict:
        current_version = self.get_current_version()
        remote_version = self.get_remote_version()
        
        result = {
            'current_version': current_version,
            'remote_version': remote_version,
            'update_available': False,
            'manifest': None
        }
        
        if remote_version and remote_version != current_version:
            result['update_available'] = True
            result['manifest'] = self.get_update_manifest()
        
        return result

if __name__ == "__main__":
    checker = EnergyManagerUpdateChecker()
    result = checker.check_for_updates()
    print(f"Update check result: {result}")


