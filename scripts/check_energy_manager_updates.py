#!/usr/bin/env python3
"""
Energy Manager Check Updates v0.2.3
"""
import sys
import os
import json
sys.path.append('/config/scripts')

from update_checker import EnergyManagerUpdateChecker

try:
    update_checker = EnergyManagerUpdateChecker(verify_ssl=False)
    result = update_checker.check_for_updates()
    
    changelog = 'No changelog available'

    os.makedirs('/config/.energy_manager', exist_ok=True)
    
    current_version = result.get('current_version', 'unknown')
    with open('/config/.energy_manager/current_version.txt', 'w') as f:
        f.write(current_version)
    
    if result.get('update_available') and result.get('manifest'):
        remote_version = result.get('remote_version', 'unknown')
        manifest = result.get('manifest', {})
        changelog = manifest.get('changelog', 'No changelog available')
        
        print(f"Updates available: {remote_version}")
        
        status_data = {
            'status': 'update_available',
            'version': remote_version,
            'changelog': changelog,
            'restart_required': manifest.get('restart_required', False)
        }
        
        with open('/config/.energy_manager/update_status.txt', 'w') as f:
            f.write(f"update_available:{remote_version}")
        with open('/config/.energy_manager/update_details.json', 'w') as f:
            json.dump(status_data, f, indent=2)
        with open('/config/.energy_manager/changelog_simple.txt', 'w') as f:
            f.write(changelog)
 
        sys.exit(1)
    elif result.get('update_available') and not result.get('manifest'):
        print(f"Update available but manifest download failed")
        with open('/config/.energy_manager/update_status.txt', 'w') as f:
            f.write(f"error:Manifest download failed")
        
        status_data = {
            'status': 'error',
            'version': 'unknown',
            'changelog': 'Update available but server error prevented downloading details',
            'restart_required': False
        }
        with open('/config/.energy_manager/update_details.json', 'w') as f:
            json.dump(status_data, f, indent=2)
        with open('/config/.energy_manager/changelog_simple.txt', 'w') as f:
            f.write(changelog)

        sys.exit(2)
    else:
        print("No updates available")
        with open('/config/.energy_manager/update_status.txt', 'w') as f:
            f.write("no_updates")
            
        status_data = {
            'status': 'no_updates',
            'version': current_version,
            'changelog': '',
            'restart_required': False
        }
        with open('/config/.energy_manager/update_details.json', 'w') as f:
            json.dump(status_data, f, indent=2)
        with open('/config/.energy_manager/changelog_simple.txt', 'w') as f:
            f.write(changelog)
            
        sys.exit(0)

except Exception as e:
    print(f"Update check failed: {e}")
    with open('/config/.energy_manager/update_status.txt', 'w') as f:
        f.write(f"error:{str(e)}")
        
    status_data = {
        'status': 'error',
        'version': 'unknown',
        'changelog': f'Error: {str(e)}',
        'restart_required': False
    }
    with open('/config/.energy_manager/update_details.json', 'w') as f:
        json.dump(status_data, f, indent=2)
        
    sys.exit(2)
