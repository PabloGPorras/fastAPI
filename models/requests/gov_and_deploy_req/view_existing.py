VIEW_EXISTING = {
            "enabled": True,  # Form-level toggle
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "request_type",
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
                            "field": "benefit_amount",
                            "required": True,
                        },
                        {
                            "field": "benifit_type",
                            "required": True,
                        },
                        {
                            "field": "approved_rik_id",
                            "required": True,
                        },
                        {
                            "field": "valid_non_sas_change_request_id",
                            "required": True,
                        },
                        {
                            "field": "errored_nonsas_governance_and_deployment_request_id",
                            "required": True,
                        }
                    ]
                }
            ]
        }