from list_values import ASSET_STATUS_LIST, BUSINESS_PROCESS_LIST, EUC_TYPE_LIST, FREQUENCY_OF_USE_LIST, RISK_RATING_LIST, YES_NO_LIST

def CREATE_NEW(search_config):
    """
    Configuration for the 'create-new' form of the EUC Request model.
    This function defines the structure and validation rules for the form.
    """

    # Define the form configuration for creating a new EUC request
    # Each field can have options, required status, and visibility conditions
    # The visibility conditions determine when a field should be shown based on other field values
    return {
            "enabled": True,  # Form-level toggle
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
                            "search_config": search_config
                        },
                        {
                            "field": "created_timestamp",
                            "required": True,
                        },
                        {
                            "field": "retired_timestamp",
                            "required": True,
                            "visibility": [
                                {"field": "asset_status", "show_if": ["RETIRED"]},
                            ],
                        },
                        {
                            "field": "retire_rationale",
                            "required": True,
                            "visibility": [
                                {"field": "asset_status", "show_if": ["RETIRED"]},
                            ],
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
                            "required": True,
                            "visibility": [
                                {"field": "frequency_of_use", "show_if": ["CRON"]},
                            ],
                        },
                        {
                            "field": "associated_controls",
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
                        },
                        {
                            "field": "path_to_item",
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
                            "exclude_from_populate": True, 
                            "options": YES_NO_LIST,
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "backup_or_archive_available",
                            "exclude_from_populate": True, 
                            "options": YES_NO_LIST,
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "evidence_of_testing",
                            "exclude_from_populate": True, 
                            "field_name": "Path to Evidence of Testing/ Data Integrity and version control",
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "does_mrm_policy_apply",
                            "exclude_from_populate": True, 
                            "options": YES_NO_LIST,
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                        {
                            "field": "date_mrm_policy_assessed",
                            "exclude_from_populate": True, 
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                                {"field": "does_mrm_policy_apply", "show_if": ["Yes"]},
                            ],
                        },
                        {
                            "field": "path_to_mrm_assessment_evidence",
                            "exclude_from_populate": True, 
                            "required": True,
                            "visibility": [
                                    {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                                    {"field": "does_mrm_policy_apply", "show_if": ["Yes"]},
                                ],
                        },
                        {
                            "field": "date_risk_rating_assessed",
                            "exclude_from_populate": True, 
                            "required": True,
                            "visibility": [
                                {"field": "request_type", "show_if": ["EUC_BUSINESS_MANAGED"]},
                            ],
                        },
                    ]
                } 
            ]
        }