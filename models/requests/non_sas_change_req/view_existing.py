from list_values import BENIFIT_TYPE_LIST, RULE_STATUS_LIST,SUB_REQUEST_TYPE_LIST

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
                            "required": True,
                        },
                        {
                            "field": "rule_name",
                            "required": True,
                        },
                        {
                            "field": "policy",
                            "required": True,
                        },
                        {
                            "field": "weight",
                            "required": True,
                        },
                        {
                            "field": "decision_type",
                            "required": True,
                        },
                        {
                            "field": "reason_code",
                            "required": True,
                        },
                        {
                            "field": "rule_status",
                            "options": RULE_STATUS_LIST,
                            "required": True,
                        },
                        {
                            "field": "output_type",
                            "required": True,
                        },
                        {
                            "field": "output_requirements",
                            "required": True,
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
                        }
                    ]
                }
            ]
        }