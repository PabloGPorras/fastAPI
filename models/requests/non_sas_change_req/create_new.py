from list_values import BENIFIT_TYPE_LIST, DECISION_TYPE_LIST, RULE_STATUS_LIST,SUB_REQUEST_TYPE_LIST

CREATE_NEW = {
            "enabled": True,  # Form-level toggle
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
                        },
                        {
                            "field": "weight",
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
                            "options": RULE_STATUS_LIST,
                        },
                        {
                            "field": "output_type",
                        },
                        {
                            "field": "output_requirements",
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