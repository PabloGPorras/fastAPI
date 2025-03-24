CREATE_NEW = {
    "enabled": True,  # Form-level toggle
    "field_groups": [
        {
            "group_name": "Basic Information",
            "fields": [
                {
                    "field": "request_type",
                    "options": ["GENERAL_REQUEST"],
                    "required": True,
                },
                {
                    "field": "request_contents",
                    "required": True,
                }
            ]
        }
    ]
}