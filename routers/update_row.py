from fastapi import APIRouter, Depends, HTTPException
from core.get_db_session import get_db_session
from services.database_service import DatabaseService
from database import logger
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/update-row/{model_name}/{row_id}")
async def update_row(
        model_name: str, 
        row_id: int, 
        data: dict,
        session: Session = Depends(get_db_session),  # Injected session dependency
        ):
    """
    Update a row dynamically based on model name.
    :param model_name: The name of the table/model to update.
    :param row_id: The ID of the row to update.
    :param data: The data to update, including relationships.
    """
    logger.info(f"Received request to update row in model '{model_name}' with ID {row_id}. Data: {data}")

    try:
        # Get the model class based on the provided model name
        model =  DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail="Model not found")

        # Fetch the main row
        row = session.query(model).filter_by(id=row_id).first()
        if not row:
            logger.warning(f"Row with ID {row_id} not found in model '{model_name}'.")
            raise HTTPException(status_code=404, detail="Row not found")

        # Update main fields
        for key, value in data.items():
            if key != "relationships" and hasattr(row, key):
                logger.debug(f"Updating field '{key}' to '{value}' in model '{model_name}'.")
                setattr(row, key, value)

        # Update relationships
        relationships = data.get("relationships", {})
        for relationship_name, related_objects in relationships.items():
            if hasattr(row, relationship_name):
                related_attribute = getattr(row, relationship_name)
                related_model = related_attribute[0].__class__ if related_attribute else None

                if not related_model:
                    logger.warning(f"Relationship model for '{relationship_name}' not found in '{model_name}'.")
                    continue

                # Clear existing relationships
                while len(related_attribute) > 0:
                    session.delete(related_attribute.pop())

                # Add updated relationships
                for related_object in related_objects:
                    new_related_row = related_model(**related_object)
                    related_attribute.append(new_related_row)

        session.commit()
        logger.info(f"Successfully updated row with ID {row_id} in model '{model_name}'.")
        return {"message": "Row updated successfully"}
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating row with ID {row_id} in model '{model_name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
