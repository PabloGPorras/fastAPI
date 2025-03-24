MAIN_SASFM_WORKFLOW = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING GOVERNANCE","APPROVAL REJECTED","USER REJECTED"], "Status_Type":["APPROVAL"]},
        "APPROVAL REJECTED": {"Roles": ["FS_Manager"], "Next": [], "Status_Type":["APPROVAL"]},  
        
        "PENDING GOVERNANCE": {"Roles": ["IMPL_Specialist"], "Next": ["PENDING UAT TABLE DETAIL","GOVERNANCE REJECTED"], "Status_Type":["GOVERNANCE"]},
        "PENDING UAT TABLE DETAIL": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","GOVERNANCE REJECTED"], "Status_Type":[]},
        "GOVERNANCE REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]}, 

        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},  
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["APPROVAL"]},  
    }
EDC_IMPL_WORKFLOW = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["ASSET APPROVAL PENDING"], "Status_Type":["APPROVAL"]},
        "ASSET APPROVAL PENDING": {"Roles": ["FS_Director"], "Next": ["DEPLOYMENT READY"], "Status_Type":["GOVERNANCE"]},
        "DEPLOYMENT READY": {"Roles": ["FS_Director"], "Next": ["DEPLOYMENT CHECKS"], "Status_Type":[]},
        "DEPLOYMENT CHECKS": {"Roles": ["FS_Director"], "Next": ["COMPLETED"], "Status_Type":["APPROVAL"]},
        "COMPLETED": {"Roles": [], "Next": [], "Status_Type":[]},
}
EDC_WORKFLOW = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING DIR APPROVAL"], "Status_Type":[]},
        "PENDING DIR APPROVAL": {"Roles": ["FS_Director"], "Next": ["COMPLETED"], "Status_Type":["APPROVAL"]},
        "COMPLETED": {"Roles": [], "Next": [], "Status_Type":[]},
}

GENERAL_REQUEST_WORKFLOW = {
        "PENDING": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","REJECTED","USER REJECTED"], "Status_Type":["GOVERNANCE"]},
        "REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]},
        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]},
}


NON_SAS_GOV_AND_DEPLOY_WORKFLOW = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING GOVERNANCE","APPROVAL REJECTED","USER REJECTED"], "Status_Type":["APPROVAL"]},
        "APPROVAL REJECTED": {"Roles": ["FS_Manager"], "Next": [], "Status_Type":[]},  
        
        "PENDING GOVERNANCE": {"Roles": ["IMPL_Specialist"], "Next": ["DEPLOYMENT READY","GOVERNANCE REJECTED"], "Status_Type":["GOVERNANCE"]},
        "GOVERNANCE REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]}, 

        "DEPLOYMENT READY": {"Roles": ["IMPL_Specialist"], "Next": ["DEPLOYMENT SUCESS CHECKS","DEPLOYMENT REJECTED"], "Status_Type":[]},
        "DEPLOYMENT REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},

        "DEPLOYMENT SUCESS CHECKS": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","DEPLOYMENT SUCESS CHECKS REJECTED"], "Status_Type":[]},
        "DEPLOYMENT SUCESS CHECKS REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":[]},

        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["COMPLETED"]},  
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["APPROVAL REJECTED"]},  
}

NON_SAS_CHANGE_REQUEST_WORKFLOW = {
        "PENDING APPROVAL": {"Roles": ["FS_Manager"], "Next": ["PENDING GOVERNANCE","APPROVAL REJECTED","USER REJECTED"], "Status_Type":["APPROVAL"]},
        "APPROVAL REJECTED": {"Roles": ["FS_Manager"], "Next": [], "Status_Type":[]},  
        
        "PENDING CODING": {"Roles": ["IMPL_Specialist"], "Next": ["COMPLETED","CODING REJECTED"], "Status_Type":["GOVERNANCE"]},
        "CODING REJECTED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["GOVERNANCE REJECTED"]}, 

        "COMPLETED": {"Roles": ["IMPL_Specialist"], "Next": [], "Status_Type":["COMPLETED"]},  
        "USER REJECTED": {"Roles": ["FS_Analyst"], "Next": [], "Status_Type":["APPROVAL REJECTED"]},  
}