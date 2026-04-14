import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\permissions\\filesystem.ts', 'FIXED: enhanced_permissions_v2.py - PermissionManager with path safety, working path checks'),
    ('src\\utils\\permissions\\pathValidation.ts', 'FIXED: enhanced_permissions_v2.py - validate_path, expand_tilde, glob_base_directory'),
    ('src\\utils\\permissions\\permissionSetup.ts', 'FIXED: enhanced_permissions_v2.py - PermissionManager setup'),
    ('src\\utils\\permissions\\permissionsLoader.ts', 'FIXED: enhanced_permissions_v2.py - load_from_dict, to_dict'),
    ('src\\utils\\permissions\\shellRuleMatching.ts', 'FIXED: enhanced_permissions_v2.py - check_shell_rule_matching'),
    ('src\\utils\\permissions\\yoloClassifier.ts', 'FIXED: enhanced_permissions_v2.py - classify_with_yolo'),
    ('src\\utils\\permissions\\PermissionUpdate.ts', 'FIXED: enhanced_permissions_v2.py - PermissionManager rule management'),
    ('src\\utils\\cronScheduler.ts', 'FIXED: cron_scheduler.py - FileLock, DistributedLock, CronScheduler'),
    ('src\\utils\\cronTasksLock.ts', 'FIXED: cron_scheduler.py - FileLock acquire/release'),
    ('src\\utils\\subprocessEnv.ts', 'FIXED: subprocess_env.py - SubprocessEnvFilter, get_filtered_env'),
    ('src\\utils\\model\\model.ts', 'FIXED: model_routing.py - ModelSelector, get_model_info'),
    ('src\\utils\\model\\providers.ts', 'FIXED: model_routing.py - MODEL_REGISTRY, route_to_api_endpoint'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

conn.close()
