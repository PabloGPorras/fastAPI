from list_values import BENIFIT_TYPE_LIST, DECISION_TYPE_LIST, RULE_STATUS_LIST,SUB_REQUEST_TYPE_LIST

VIEW_EXISTING = {
            "enabled": False,  # Form-level toggle
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "request_type",
                            "options": ["NON_SAS_CHANGE_REQUEST"],
                            "required": True,
                        },
                        {
                            "field": "sub_request_type",
                            "options": SUB_REQUEST_TYPE_LIST,
                            "required": True,
                        },
                        {
                            "field": "short_description",
                            "required": True,
                        },
                        {
                            "field": "requirements",
                            "required": True,
                        },
                        {
                            "field": "rule_id",
                        },
                        {
                            "field": "rule_name",
                        },
                        {
                            "field": "policy",
                            "field_name": "Policy/strategy",
                        },
                        {
                            "field": "weight",
                            "field_name": "Weight/priority",
                        },
                        {
                            "field": "decision_type",
                            "options": DECISION_TYPE_LIST,
                        },
                        {
                            "field": "reason_code",
                        },
                        {
                            "field": "rule_status",
                            "field_name": "Active/inactive",
                            "options": RULE_STATUS_LIST,
                        },
                        {
                            "field": "output_type",
                            "field_name": "Output queue / case details output/ channel output",
                        },
                        {
                            "field": "output_requirements",
                            "field_name": "Output requirements (decision, rule outputs, risk level code)",
                        },
                        {
                            "field": "benefit_amount",
                            "required": True,
                        },
                        {
                            "field": "benifit_type",
                            "options": BENIFIT_TYPE_LIST,
                            "required": True,
                        },
                        {
                            "field": "rik_id",
                            "required": True,
                        },
                        {
                            "field": "errored_non_sas_change_request_field",
                            "required": True,
                        }
                    ]
                }
            ]
        }