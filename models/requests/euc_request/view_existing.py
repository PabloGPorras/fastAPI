from list_values import ASSET_STATUS_LIST, BUSINESS_PROCESS_LIST, EUC_TYPE_LIST, FREQUENCY_OF_USE_LIST, RISK_RATING_LIST, YES_NO_LIST

VIEW_EXISTING = {
            "enabled": False,  # Form-level toggle
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "request_type",
                            "options": ["EUC_IMPL_TEAM_MANAGED","EUC_BUSINESS_MANAGED"],
                            "required": True,
                        },
                        {
                            "field": "euc_name",
                            "required": True,
                        },
                        {
                            "field": "created_timestamp",
                            "required": True,
                        },
                        {
                            "field": "retired_timestamp",
                            "required": True,
                        },
                        {
                            "field": "retire_rationale",
                            "required": True,
                        },
                        {
                            "field": "asset_status",
                            "options": ASSET_STATUS_LIST,
                            "required": True,
                        },
                        {
                            "field": "business_process",
                            "options": BUSINESS_PROCESS_LIST,
                            "required": True,
                        },
                        {
                            "field": "euc_director",
                            "required": True,
                        },
                        {
                            "field": "euc_owner",
                            "required": True,
                        },
                        {
                            "field": "asset_description",
                            "required": True,
                        },
                        {
                            "field": "euc_type",
                            "options": EUC_TYPE_LIST,
                            "required": True,
                        },
                        {
                            "field": "risk_rating",
                            "options": RISK_RATING_LIST,
                            "required": True,
                        },
                        {
                            "field": "risk_rating_rationale",
                            "required": True,
                        },
                        {
                            "field": "frequency_of_use",
                            "options": FREQUENCY_OF_USE_LIST,
                            "required": True,
                        },
                        {
                            "field": "cron_schedule",
                            "visibility": [
                                {"field": "frequency_of_use", "show_if": ["CRON"]},
                            ],
                            "required": True,
                        },
                        {
                            "field": "associated_controls",
                            "required": True,
                        },
                        {
                            "field": "document_file_type",
                            "required": True,
                        },
                        {
                            "field": "application_system",
                            "required": True,
                        },
                        {
                            "field": "euc_control_checklist_file_path",
                            "required": True,
                            "visibility": [
                                {"field": "risk_rating", "show_if": ["Critical","High"]},
                            ],
                        },
                        {
                            "field": "euc_file_path",
                            "required": True,
                        },
                        {
                            "field": "item_type",
                            "required": True,
                        },
                        {
                            "field": "path_to_item",
                            "required": True,
                        },
                        {
                            "field": "changes_made_and_why",
                            "required": True,
                        }
                    ]
                },
                {
                    "group_name": "",
                    "fields": [
                        {
                            "field": "asset_has_role_based_security",
                            "options": YES_NO_LIST,
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "backup_or_archive_available",
                            "options": YES_NO_LIST,
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "evidence_of_testing",
                            "field_name": "Path to Evidence of Testing/ Data Integrity and veresion control",
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "does_mrm_policy_apply",
                            "options": YES_NO_LIST,
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "date_mrm_policy_assessed",
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                                {"field": "does_mrm_policy_apply", "show_if": ["Yes"]},
                            ],
                        },
                        {
                            "field": "path_to_mrm_assessment_evidence",
                            "required": True,
                        "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                                {"field": "does_mrm_policy_apply", "show_if": ["Yes"]},
                            ],
                        },
                        {
                            "field": "date_risk_rating_assessed",
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                    ]
                } 
            ]
        }