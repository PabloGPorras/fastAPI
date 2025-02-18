import csv
import io
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.get_db_session import get_db_session
from core.get_current_user import get_current_user
from database import logger
from models.user import User
from services.database_service import DatabaseService
from services.request_service import assign_group_id, create_rms_request, filter_and_clean_data, get_column_mappings, get_model

router = APIRouter()


@router.post("/bulk-import")
async def bulk_import(
    file: UploadFile,
    model_name: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """
    Bulk imports data from a CSV file into the specified model.
    """
    logger.info(f"Received bulk import request for model: {model_name}. File: {file.filename}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        model = get_model(model_name)  # ✅ Reuses get_model()

        # Read CSV content
        content = await file.read()
        csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

        # Get expected headers from model metadata
        metadata = DatabaseService.gather_model_metadata(model, session=session, form_name="create-new")
        expected_headers = [col["name"] for col in metadata["columns"]]

        if metadata["is_request"]:
            expected_headers.extend([
                "organization",
                "sub_organization",
                "line_of_business",
                "team",
                "decision_engine",
                "effort"    

            ])

        # Validate CSV headers
        file_headers = csv_reader.fieldnames
        if not file_headers or any(header not in expected_headers for header in file_headers):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CSV headers. Expected headers: {', '.join(expected_headers)}",
            )

        logger.debug(f"CSV headers found in uploaded file: {file_headers}")


        # Process rows
        objects_to_add = []
        group_id = assign_group_id({})  # ✅ Generates group_id
        row_count = 0

        for row in csv_reader:
            row_count += 1
            logger.debug(f"Processing row {row_count}: {row}")

            # ✅ Create RmsRequest if the model is a request type
            if metadata["is_request"]:
                new_request, new_status = create_rms_request(model, row, group_id, user)
                objects_to_add.extend([new_request, new_status])

            # ✅ Process model-specific data
            column_mappings, allowed_keys, required_columns = get_column_mappings(model)
            logger.debug(f"Column mappings: {column_mappings}, Allowed keys: {allowed_keys}, Required columns: {required_columns}")
            row_data = filter_and_clean_data(row, allowed_keys, required_columns, column_mappings, model)
            row_data["unique_ref"] = new_request.unique_ref if metadata["is_request"] else None

            # ✅ Create the main object
            instance = model(**row_data)
            objects_to_add.append(instance)

        # ✅ Add all objects in bulk
        session.add_all(objects_to_add)
        session.commit()

        logger.info(f"Bulk import completed successfully. Total rows processed: {row_count}")
        return {"message": "Bulk import completed successfully!", "group_id": group_id}

    except Exception as e:
        session.rollback()
        logger.error(f"Error processing bulk import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
