from list_values import BENIFIT_TYPE_LIST

CREATE_NEW = {
            "enabled": True,  # Form-level toggle
            "field_groups": [
                {
                    "group_name": "Basic Information",
                    "fields": [
                        {
                            "field": "request_type",
                            "options": ["NON_SAS_GOV_AND_DEPLOY"],
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
                            "field": "benefit_amount",
                            "required": True,
                        },
                        {
                            "field": "benifit_type",
                            "options": BENIFIT_TYPE_LIST,
                            "required": True,
                        },
                        {
                            "field": "approved_rik_id",
                        },
                        {
                            "field": "valid_non_sas_change_request_id",
                        },
                        {
                            "field": "errored_nonsas_governance_and_deployment_request_id",
                        }
                    ]
                }
            ]
        }