RULE_WORKFLOW = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING GOVERNANCE","APPROVAL REJECTED","USER REJECTED"], "Status_Type":["APPROVAL"]},
        "APPROVAL REJECTED": {"Roles": ["FS_Manager"], "Next": [], "Status_Type":["APPROVAL"]},  
        
        "PENDING GOVERNANCE": {"Roles": ["IMPL_Specialist"], "Next": ["PENDING UAT TABLE DETAIL","GOVERNANCE REJECTED"], "Status_Type":["GOVERNANCE"]},
        "PENDING UAT TABLE DETAIL": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","GOVERNANCE REJECTED"], "Status_Type":[]},
        "GOVERNANCE REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]}, 

        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},  
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["APPROVAL"]},  
    }

