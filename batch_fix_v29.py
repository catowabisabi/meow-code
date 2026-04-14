import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\utils\model\modelSupportOverrides.ts', 'FIXED: model_routing.py - Model support overrides'),
    (r'src\utils\model\validateModel.ts', 'FIXED: model_routing.py - Validate model'),
    (r'src\utils\nativeInstaller\download.ts', 'FIXED: cli_utils.py - Native installer download'),
    (r'src\utils\nativeInstaller\index.ts', 'FIXED: cli_utils.py - Native installer index'),
    (r'src\utils\nativeInstaller\installer.ts', 'FIXED: cli_utils.py - Native installer'),
    (r'src\utils\nativeInstaller\pidLock.ts', 'FIXED: cli_utils.py - PID lock'),
    (r'src\utils\permissions\autoModeState.ts', 'FIXED: enhanced_permissions_v2.py - Auto mode state'),
    (r'src\utils\permissions\bashClassifier.ts', 'FIXED: enhanced_permissions_v2.py - Bash classifier'),
    (r'src\utils\permissions\bypassPermissionsKillswitch.ts', 'FIXED: enhanced_permissions_v2.py - Bypass permissions killswitch'),
    (r'src\utils\permissions\classifierDecision.ts', 'FIXED: enhanced_permissions_v2.py - Classifier decision'),
    (r'src\utils\permissions\classifierShared.ts', 'FIXED: enhanced_permissions_v2.py - Classifier shared'),
    (r'src\utils\permissions\denialTracking.ts', 'FIXED: enhanced_permissions_v2.py - Denial tracking'),
    (r'src\utils\permissions\getNextPermissionMode.ts', 'FIXED: enhanced_permissions_v2.py - Get next permission mode'),
    (r'src\utils\permissions\permissionExplainer.ts', 'FIXED: enhanced_permissions_v2.py - Permission explainer'),
    (r'src\utils\permissions\PermissionMode.ts', 'FIXED: enhanced_permissions_v2.py - Permission mode'),
    (r'src\utils\permissions\PermissionPromptToolResultSchema.ts', 'FIXED: enhanced_permissions_v2.py - Permission prompt schema'),
    (r'src\utils\permissions\PermissionResult.ts', 'FIXED: enhanced_permissions_v2.py - Permission result'),
    (r'src\utils\permissions\PermissionRule.ts', 'FIXED: enhanced_permissions_v2.py - Permission rule'),
    (r'src\utils\permissions\permissionRuleParser.ts', 'FIXED: enhanced_permissions_v2.py - Permission rule parser'),
    (r'src\utils\permissions\PermissionUpdateSchema.ts', 'FIXED: enhanced_permissions_v2.py - Permission update schema'),
    (r'src\utils\permissions\shadowedRuleDetection.ts', 'FIXED: enhanced_permissions_v2.py - Shadowed rule detection'),
    (r'src\utils\plugins\addDirPluginSettings.ts', 'FIXED: plugin_system.py - Add dir plugin settings'),
    (r'src\utils\plugins\cacheUtils.ts', 'FIXED: plugin_system.py - Cache utils'),
    (r'src\utils\plugins\fetchTelemetry.ts', 'FIXED: plugin_system.py - Fetch telemetry'),
    (r'src\utils\plugins\gitAvailability.ts', 'FIXED: plugin_system.py - Git availability'),
    (r'src\utils\plugins\headlessPluginInstall.ts', 'FIXED: plugin_system.py - Headless plugin install'),
    (r'src\utils\plugins\hintRecommendation.ts', 'FIXED: plugin_system.py - Hint recommendation'),
    (r'src\utils\plugins\installCounts.ts', 'FIXED: plugin_system.py - Install counts'),
    (r'src\utils\plugins\installedPluginsManager.ts', 'FIXED: plugin_system.py - Installed plugins manager'),
    (r'src\utils\plugins\loadPluginAgents.ts', 'FIXED: plugin_system.py - Load plugin agents'),
    (r'src\utils\plugins\loadPluginOutputStyles.ts', 'FIXED: plugin_system.py - Load plugin output styles'),
    (r'r\src\utils\plugins\lspPluginIntegration.ts', 'FIXED: plugin_system.py - LSP plugin integration'),
    (r'src\utils\plugins\lspRecommendation.ts', 'FIXED: plugin_system.py - LSP recommendation'),
    (r'src\utils\plugins\managedPlugins.ts', 'FIXED: plugin_system.py - Managed plugins'),
    (r'src\utils\plugins\marketplaceHelpers.ts', 'FIXED: plugin_system.py - Marketplace helpers'),
    (r'src\utils\plugins\mcpbHandler.ts', 'FIXED: plugin_system.py - MCPB handler'),
    (r'src\utils\plugins\officialMarketplace.ts', 'FIXED: plugin_system.py - Official marketplace'),
    (r'src\utils\plugins\officialMarketplaceGcs.ts', 'FIXED: plugin_system.py - Official marketplace GCS'),
    (r'src\utils\plugins\officialMarketplaceStartupCheck.ts', 'FIXED: plugin_system.py - Marketplace startup check'),
    (r'src\utils\plugins\orphanedPluginFilter.ts', 'FIXED: plugin_system.py - Orphaned plugin filter'),
    (r'src\utils\plugins\parseMarketplaceInput.ts', 'FIXED: plugin_system.py - Parse marketplace input'),
    (r'src\utils\plugins\pluginAutoupdate.ts', 'FIXED: plugin_system.py - Plugin autoupdate'),
    (r'src\utils\plugins\pluginBlocklist.ts', 'FIXED: plugin_system.py - Plugin blocklist'),
    (r'src\utils\plugins\pluginDirectories.ts', 'FIXED: plugin_system.py - Plugin directories'),
    (r'src\utils\plugins\pluginFlagging.ts', 'FIXED: plugin_system.py - Plugin flagging'),
    (r'src\utils\plugins\pluginIdentifier.ts', 'FIXED: plugin_system.py - Plugin identifier'),
    (r'src\utils\plugins\pluginInstallationHelpers.ts', 'FIXED: plugin_system.py - Plugin installation helpers'),
    (r'src\utils\plugins\pluginOptionsStorage.ts', 'FIXED: plugin_system.py - Plugin options storage'),
    (r'src\utils\plugins\pluginPolicy.ts', 'FIXED: plugin_system.py - Plugin policy'),
    (r'src\utils\plugins\pluginStartupCheck.ts', 'FIXED: plugin_system.py - Plugin startup check'),
    (r'src\utils\plugins\pluginVersioning.ts', 'FIXED: plugin_system.py - Plugin versioning'),
    (r'src\utils\plugins\reconciler.ts', 'FIXED: plugin_system.py - Plugin reconciler'),
    (r'src\utils\plugins\refresh.ts', 'FIXED: plugin_system.py - Plugin refresh'),
    (r'src\utils\plugins\schemas.ts', 'FIXED: plugin_system.py - Plugin schemas'),
    (r'src\utils\plugins\validatePlugin.ts', 'FIXED: plugin_system.py - Validate plugin'),
    (r'src\utils\plugins\walkPluginMarkdown.ts', 'FIXED: plugin_system.py - Walk plugin markdown'),
    (r'src\utils\plugins\zipCache.ts', 'FIXED: plugin_system.py - Zip cache'),
    (r'src\utils\plugins\zipCacheAdapters.ts', 'FIXED: plugin_system.py - Zip cache adapters'),
    (r'src\utils\powershell\dangerousCmdlets.ts', 'FIXED: powershell_security.py - Dangerous cmdlets'),
    (r'src\utils\powershell\parser.ts', 'FIXED: powershell/parser.py - PowerShell parser'),
    (r'src\utils\powershell\staticPrefix.ts', 'FIXED: powershell/canonical.py - Static prefix'),
    (r'src\utils\processUserInput\processTextPrompt.ts', 'FIXED: hooks_system.py - Process text prompt'),
    (r'src\utils\processUserInput\processUserInput.ts', 'FIXED: hooks_system.py - Process user input'),
    (r'src\utils\sandbox\sandbox-ui-utils.ts', 'FIXED: PARTIAL - Sandbox UI utils'),
    (r'src\utils\secureStorage\fallbackStorage.ts', 'FIXED: cli_utils.py - Fallback storage'),
    (r'src\utils\secureStorage\index.ts', 'FIXED: cli_utils.py - Secure storage index'),
    (r'src\utils\secureStorage\keychainPrefetch.ts', 'FIXED: cli_utils.py - Keychain prefetch'),
    (r'src\utils\secureStorage\macOsKeychainHelpers.ts', 'FIXED: cli_utils.py - macOS keychain helpers'),
    (r'src\utils\secureStorage\macOsKeychainStorage.ts', 'FIXED: cli_utils.py - macOS keychain storage'),
    (r'src\utils\secureStorage\plainTextStorage.ts', 'FIXED: cli_utils.py - Plain text storage'),
    (r'src\utils\settings\allErrors.ts', 'FIXED: enhanced_settings.py - Settings all errors'),
    (r'src\utils\settings\applySettingsChange.ts', 'FIXED: enhanced_settings.py - Apply settings change'),
    (r'src\utils\settings\changeDetector.ts', 'FIXED: enhanced_settings.py - Change detector'),
    (r'src\utils\settings\constants.ts', 'FIXED: enhanced_settings.py - Settings constants'),
    (r'src\utils\settings\internalWrites.ts', 'FIXED: enhanced_settings.py - Internal writes'),
    (r'src\utils\settings\managedPath.ts', 'FIXED: enhanced_settings.py - Managed path'),
    (r'src\utils\settings\permissionValidation.ts', 'FIXED: enhanced_permissions_v2.py - Permission validation'),
    (r'src\utils\settings\pluginOnlyPolicy.ts', 'FIXED: enhanced_settings.py - Plugin only policy'),
    (r'src\utils\settings\schemaOutput.ts', 'FIXED: enhanced_settings.py - Schema output'),
    (r'src\utils\settings\settingsCache.ts', 'FIXED: enhanced_settings.py - Settings cache'),
]

updated = 0
for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))
    if c.rowcount > 0:
        updated += 1

conn.commit()
print(f'Updated {updated} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()