UPDATE agents SET
    name = 'Chris DevOps',
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
WHERE name = 'DevOps 工程師';