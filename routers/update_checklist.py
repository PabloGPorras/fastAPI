from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from core.get_db_session import get_db_session
import json
from services.database_service import DatabaseService

router = APIRouter()

@router.post("/update-checklist/{model_name}")
async def update_checklist(
    model_name: str,  # Name of the model to use
    request: Request,  # Use Request to process dynamic form data
    session: Session = Depends(get_db_session),  # Injected session dependency
):
    try:
        # Resolve the model dynamically from the model_name
        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=400, detail=f"Invalid model name: {model_name}")

        # Parse form data from the request
        form_data = await request.form()
        unique_ref = form_data.get("unique_ref")  # Get unique_ref
        checklist_values = {
            key.split("[")[1][:-1]: value.lower() == "true"
            for key, value in form_data.items()
            if key.startswith("checklist_values[")
        }
        # Extract all other fields except unique_ref and checklist_values
        checklist_fields = {
            key: form_data.get(key)
            for key in form_data.keys()
            if key not in ["unique_ref", "checklist_values","governance"]
        }

        # Fetch the object by unique_ref
        instance = session.query(model).filter_by(unique_ref=unique_ref).one_or_none()
        if not instance:
            raise HTTPException(status_code=404, detail=f"{model_name} not found.")


        # Update all dynamic fields in the model
        for field, value in checklist_fields.items():
            if hasattr(instance, field):
                setattr(instance, field, value)

        # Update governance column with JSON data
        if hasattr(instance, "governance"):
            instance.governance = json.dumps(checklist_values)
        else:
            raise HTTPException(status_code=400, detail=f"{model_name} does not have a 'governance' field.")

        session.commit()

        return {"message": f"Checklist for {model_name} updated successfully.", "governance": checklist_values}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

