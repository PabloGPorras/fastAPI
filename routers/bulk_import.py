import csv
import io
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import inspect
from get_current_user import get_current_user
from services.database_service import DatabaseService
from example_model import RmsRequest, RmsRequestStatus, User, id_method
from database import logger, SessionLocal

router = APIRouter()

@router.post("/bulk-import")
async def bulk_import(
    file: UploadFile,
    model_name: str = Form(...),
    user: User = Depends(get_current_user),
):
    logger.info(f"Received bulk import request for model: {model_name}. File name: {file.filename}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Validate model name
    model = DatabaseService.get_model_by_tablename(model_name)
    if not model:
        logger.warning(f"Model '{model_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

    # Validate file type
    if not file.filename.endswith(".csv"):
        logger.warning(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Parse the CSV file
    content = await file.read()
    try:
        csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        logger.error(f"Error decoding file content: {e}")
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

    # Get expected headers for validation
    session = SessionLocal()
    try:
        metadata = DatabaseService.gather_model_metadata(
            model, session=session, form_name="create-new"
        )
        expected_headers = [col["name"] for col in metadata["columns"]]
        if metadata["is_request"]:
            expected_headers.extend([
                "rms_request.organization",
                "rms_request.sub_organization",
                "rms_request.line_of_business",
                "rms_request.team",
                "rms_request.decision_engine",
            ])

        # Validate file headers
        file_headers = csv_reader.fieldnames
        if not file_headers or any(header not in expected_headers for header in file_headers):
            logger.warning(f"Invalid headers: {file_headers}. Expected: {expected_headers}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CSV headers. Expected headers: {', '.join(expected_headers)}",
            )

        # Process rows
        row_count = 0
        group_id = id_method()  # Generate a unique group ID

        for row in csv_reader:
            row_count += 1
            logger.debug(f"Processing row {row_count}: {row}")

            # Extract and validate RmsRequest fields
            rms_request_data = {
                "organization": row.get("rms_request.organization"),
                "sub_organization": row.get("rms_request.sub_organization"),
                "line_of_business": row.get("rms_request.line_of_business"),
                "team": row.get("rms_request.team"),
                "decision_engine": row.get("rms_request.decision_engine"),
                "group_id": group_id,
                "requester": user.user_name,
                "request_type": model_name.upper(),
                "effort": "BAU",
            }

            # Create a new RmsRequest
            rms_request = RmsRequest(**rms_request_data)
            session.add(rms_request)
            session.flush()  # Generate ID for rms_request

            # Insert the initial status for the RmsRequest
            initial_status = list(model.request_status_config.keys())[0]  # Get the first status
            rms_status = RmsRequestStatus(
                unique_ref=rms_request.unique_ref,  # Use the correct field name
                status=initial_status,
                user_name=user.user_name,  # Replace with the actual user performing the import
            )
            session.add(rms_status)

            # Extract and validate model-specific fields
            model_fields = {col["name"] for col in metadata["columns"]}
            data = {field: row[field] for field in model_fields if field in row}
            data["rms_request_id"] = rms_request.unique_ref  # Associate with the RmsRequest

            # Create a new instance of the model
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
