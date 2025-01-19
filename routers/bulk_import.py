import csv
import io
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import inspect
from get_current_user import get_current_user
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User, id_method
from database import logger,SessionLocal


router = APIRouter()

@router.post("/bulk-import")
async def bulk_import(file: UploadFile, model_name: str = Form(...),user: User = Depends(get_current_user)):
    logger.info(f"Received bulk import request for model: {model_name}. File name: {file.filename}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Validate model name
    model =  DatabaseService.get_model_by_tablename(model_name)
    if not model:
        logger.warning(f"Model '{model_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

    # Validate file type
    if not file.filename.endswith(".csv"):
        logger.warning(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Parse the CSV file
    content = await file.read()
    logger.info(f"File received: {file.filename}")
    logger.info(f"File content preview: {content[:100]}")  # Check the first 100 bytes

    try:
        csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        logger.error(f"Error decoding file content: {e}")
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

    session = SessionLocal()
    try:
        row_count = 0
        group_id = id_method()  # Generate a unique group ID

        for row in csv_reader:
            row_count += 1
            logger.debug(f"Processing row {row_count}: {row}")

            # Create a new RmsRequest
            rms_request = RmsRequest(
                requester=user.user_name,  # Provide default or dynamic values as needed
                request_type="RULE DEPLOYMENT",
                effort="BAU",
                organization="FRM",
                sub_organization="FRAP",
                line_of_business="CREDIT",
                team="IMPL",
                decision_engine="SASFM",
                group_id=group_id,
            )
            session.add(rms_request)
            session.flush()  # Flush to generate an ID for rms_request

            # Insert the initial status for the RmsRequest
            initial_status = list(model.request_status_config.keys())[0]  # Get the first status
            rms_status = RmsRequestStatus(
                request_id=rms_request.unique_ref,
                status=initial_status,
                user_name=user.user_name,  # Replace with actual user performing the import
            )
            session.add(rms_status)

            # Extract relevant fields for the RuleRequest model
            model_fields = {col.name for col in inspect(model).columns}
            data = {field: row[field] for field in model_fields if field in row}
            data["rms_request_id"] = rms_request.unique_ref  # Associate with the newly created RmsRequest

            # Create the RuleRequest
            instance = model(**data)
            session.add(instance)

        session.commit()
        logger.info(f"Bulk import completed successfully. Total rows processed: {row_count}")
        return {"message": "Bulk import completed successfully!", "group_id": group_id}
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing bulk import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        session.close()
        logger.debug("Database session closed.")