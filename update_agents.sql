-- Bulk update all agents with Chris's config
-- Run with: docker exec -i clawith-postgres-1 psql -U clawith -d clawith -f /tmp/update_agents.sql

-- Alex (AI Engineer)
UPDATE agents SET
    name = 'Alex AI Engineer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = 'AI 工程師 A';

-- Brian (API Integration Engineer)
UPDATE agents SET
    name = 'Brian API Engineer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = 'API 整合工程師';

-- Diana (UI Designer)
UPDATE agents SET
    name = 'Diana UI Designer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = 'UI 設計師';

-- Evan (UX Designer)
UPDATE agents SET
    name = 'Evan UX Designer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = 'UX 設計師';

-- Fiona (HR Admin)
UPDATE agents SET
    name = 'Fiona HR Admin',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '人事行政';

-- Gary (Content Marketer)
UPDATE agents SET
    name = 'Gary Content Marketer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '內容行銷員';

-- Hannah (Frontend QA)
UPDATE agents SET
    name = 'Hannah Frontend QA',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '前端 QA 工程師';

-- Ian (Frontend Engineer A)
UPDATE agents SET
    name = 'Ian Frontend Engineer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '前端工程師 A';

-- Jack (Partner Manager)
UPDATE agents SET
    name = 'Jack Partner Manager',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '合作夥伴經理';

-- Joey (Compliance)
UPDATE agents SET
    name = 'Joey Compliance',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '合規專員 Joey';

-- Kevin (Security Engineer)
UPDATE agents SET
    name = 'Kevin Security Engineer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '安全工程師';

-- Lisa (Account Executive)
UPDATE agents SET
    name = 'Lisa Account Executive',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '客戶主任';

-- Mike (Customer Success)
UPDATE agents SET
    name = 'Mike Customer Success',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '客戶成功經理';

-- Nina (Graphic Designer)
UPDATE agents SET
    name = 'Nina Graphic Designer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '平面設計師';

-- Oliver (Backend QA)
UPDATE agents SET
    name = 'Oliver Backend QA',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '後端 QA 工程師';

-- Peter (Backend Engineer A)
UPDATE agents SET
    name = 'Peter Backend Engineer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '後端工程師 A';

-- Quincy (Backend Engineer B)
UPDATE agents SET
    name = 'Quincy Backend Engineer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '後端工程師 B';

-- Rachel (Tech Support A)
UPDATE agents SET
    name = 'Rachel Tech Support',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '技術支援 A';

-- Steve (Data Engineer)
UPDATE agents SET
    name = 'Steve Data Engineer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '數據工程師';

-- Tom (Digital Marketer)
UPDATE agents SET
    name = 'Tom Digital Marketer',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '數碼行銷員';

-- Uma (BDM Hong Kong)
UPDATE agents SET
    name = 'Uma BDM Hong Kong',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '業務發展經理 (HK)';

-- Victor (Operations Manager)
UPDATE agents SET
    name = 'Victor Operations Manager',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '營運經理';

-- Wendy (Automation QA)
UPDATE agents SET
    name = 'Wendy Automation QA',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '自動化 QA 工程師';

-- Xavier (Finance)
UPDATE agents SET
    name = 'Xavier Finance',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '財務會計';

-- Yolanda (Risk Audit)
UPDATE agents SET
    name = 'Yolanda Risk Audit',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = '風險審計分析師';

-- Zara (Meeseeks)
UPDATE agents SET
    name = 'Zara Meeseeks',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = 'Meeseeks';

-- Nova (OKR Agent)
UPDATE agents SET
    name = 'Nova OKR Agent',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = 'OKR Agent';

-- Morty (placeholder agent)
UPDATE agents SET
    name = 'Morty Agent',
    primary_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    fallback_model_id = '44f7ef15-9d3b-4c47-bcd4-435467fd6d64',
    autonomy_policy = '{"read_files":"L1","write_workspace_files":"L2","send_feishu_message":"L2","send_external_message":"L2","modify_soul":"L3","access_business_system_read":"L1","access_business_system_write":"L1","delete_files":"L2","create_calendar_event":"L2","financial_operations":"L3"}',
    max_tokens_per_day = 400000,
    max_tokens_per_month = 10000000,
    context_window_size = 500,
    max_tool_rounds = 1600,
    max_triggers = 600,
    max_llm_calls_per_day = 6000,
    heartbeat_enabled = true,
    heartbeat_interval_minutes = 30,
    heartbeat_active_hours = '01:00-23:00',
    timezone = 'Asia/Hong_Kong'
WHERE name = 'Morty';

-- Commit all changes
COMMIT;