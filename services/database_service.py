from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.inspection import inspect
from example_model import Base, RmsRequest, RmsRequestStatus
from sqlalchemy.ext.declarative import DeclarativeMeta
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    @staticmethod
    def fetch_model_rows(model_name: str, session: Session, model):
        """
        Fetch rows for a given model dynamically. Handles special cases like 'request'.

        Args:
            model_name (str): Name of the model/table.
            session (Session): SQLAlchemy session.
            model: SQLAlchemy model class.

        Returns:
            list: Rows fetched from the database.
        """

        subquery = (
            session.query(
                RmsRequestStatus.unique_ref,
                func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
            )
            .group_by(RmsRequestStatus.unique_ref)
            .subquery()
        )
        
        rows = []
        # Query data based on the model name
        if model_name == "request":
            rows = (
                session.query(
                    RmsRequest,  # Directly query RmsRequest
                    RmsRequestStatus.status.label("request_status"),  # Fetch the status
                )
                .join(subquery, RmsRequest.unique_ref == subquery.c.unique_ref)  # Join with subquery
                .all()
            )
        else:
            try:
                rows = (
                    session.query(
                        model,  # Dynamic model (e.g., RuleRequest)
                        RmsRequestStatus.status.label("request_status"),  # Explicitly fetch the status
                        RmsRequest.group_id.label("group_id"),  # Fetch group_id from RmsRequest
                    )
                    .join(RmsRequest, model.rms_request_id == RmsRequest.unique_ref)  # Join with RmsRequest
                    .join(subquery, RmsRequest.unique_ref == subquery.c.unique_ref)  # Join to find latest status
                    .all()
                )
            except:
                rows = session.query(model).all()

        return rows

    @staticmethod
    def transform_rows_to_dicts(rows, model):
        """
        Transform rows into a dictionary format with transitions.

        Args:
            rows: List of database rows to transform.
            model: SQLAlchemy model class associated with the rows.

        Returns:
            list: Transformed list of dictionaries with row data and transitions.
        """
        row_dicts = []
        mapper = inspect(model)

        for row in rows:
            try:
                # Handle rows with additional metadata (e.g., status and group_id)
                if len(row) == 3:  # Assume structure: (ModelInstance, request_status, group_id)
                    model_obj, request_status, group_id = row
                elif len(row) == 2:  # Assume structure: (ModelInstance, request_status)
                    model_obj, request_status = row
                    group_id = getattr(model_obj, "group_id", None)
                else:  # Assume single-object rows
                    model_obj = row
                    request_status = None
                    group_id = getattr(model_obj, "group_id", None)

                # Extract column data from the model
                row_data = {}
                for col in mapper.columns:
                    val = getattr(model_obj, col.name, None)
                    # Convert datetime objects to ISO 8601 strings
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    row_data[col.name] = val

                # Add request_status and group_id
                row_data["request_status"] = request_status
                row_data["group_id"] = group_id

                # Fetch transitions based on the current request_status
                if request_status and hasattr(model, "request_status_config"):
                    transitions = model.request_status_config.get(request_status, {}).get("Next", [])
                    row_data["transitions"] = [
                        {"next_status": next_status, "action_label": f"Change to {next_status}"}
                        for next_status in transitions
                    ]
                else:
                    row_data["transitions"] = []

            except (TypeError, ValueError):
                # Handle errors gracefully for single-object rows
                row_data = {}
                for col in mapper.columns:
                    val = getattr(row, col.name, None)
                    row_data[col.name] = val

                # Default values for rows without explicit metadata
                row_data["request_status"] = None
                row_data["group_id"] = getattr(row, "group_id", None)
                row_data["transitions"] = []

            row_dicts.append(row_data)

        return row_dicts
    
    @staticmethod
    def get_all_models():
        """
        Dynamically fetch all models with their `is_request` attribute and `request_menu_category`.

        Returns:
            list: List of dictionaries with model metadata, including names, URLs, `is_request`, and `request_menu_category`.
        """
        models_with_metadata = []
        for mapper in Base.registry.mappers:  # Loop through all registered mappers
            cls = mapper.class_
            if isinstance(cls, DeclarativeMeta):  # Ensure it's a valid SQLAlchemy model
                is_request = getattr(cls, "is_request", False)
                request_menu_category = getattr(cls, "request_menu_category", "")
                
                models_with_metadata.append({
                    "name": cls.__tablename__.replace("_", " ").capitalize(),
                    "url": f"/{cls.__tablename__}",
                    "model_name": cls.__tablename__,
                    "is_request": is_request,
                    "request_menu_category": request_menu_category
                })
        return models_with_metadata

    @staticmethod
    def gather_model_metadata(model, session: Session, form_name: str = None):
        """
        Gather metadata from the given SQLAlchemy model.
        Args:
            model: SQLAlchemy model class.
            session: SQLAlchemy session for querying related data.
            form_name: The name of the form to filter fields and relationships based on visibility.

        Returns:
            dict: A dictionary containing metadata (columns, form fields, relationships, etc.).
        """
        if not model:
            raise ValueError("Model cannot be None.")

        mapper = inspect(model)
        is_request = getattr(model, "is_request", False)
        logger.debug(f"Retrieved 'is_request' for model '{model.__name__}': {is_request}")

        metadata = {
            "columns": [],
            "form_fields": [],
            "relationships": [],
            "predefined_options": {},
            "is_request": getattr(model, "is_request", False),
            "request_menu_category": getattr(model, "request_menu_category", None),
            "request_status_config": getattr(model, "request_status_config", None),
        }
        logger.debug(f"Retrieved 'metadata' for model '{model.__name__}': {metadata}")


        def is_visible(info):
            """
            Determine if a field or relationship is visible for the given form.
            """
            if not form_name:
                logger.debug("No form_name provided. Defaulting to visible.")
                return True  # Default to visible if no form_name provided
            if info and "form_visibility" in info:
                visibility = info["form_visibility"].get(form_name, True)
                logger.debug(f"Visibility for {form_name}: {visibility}")
                return visibility
            logger.debug("Info missing or no form_visibility specified. Defaulting to visible.")
            return True

        # Extract column metadata
        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "options": getattr(model, f"{column.name}_options", None),
                "multi_options": getattr(model, f"{column.name}_multi_options", None),
                "is_foreign_key": bool(column.foreign_keys),
            }
            metadata["columns"].append(column_info)
            logger.debug(f"Retrieved {column.name} metadata: %s", column_info)

            # Include in form fields only if visible for the given form
            if is_visible(getattr(column, "info", {})) and column.name not in ["unique_ref"]:
                metadata["form_fields"].append(column_info)
                logger.debug(f"Added {column.name} to form fields: {is_visible(getattr(column, 'info', {}))}")

        # Add `group_id` column for is_request models
        if metadata["is_request"]:
            metadata["columns"].insert(1, {"name": "group_id", "type": "String", "options": None})

        # Add a dynamic column for `request_status` if relevant
        if metadata["is_request"]:
            metadata["columns"].insert(1, {"name": "request_status", "type": "String", "options": None})

        # Extract relationship data dynamically
        for rel in mapper.relationships:
            relationship_info = {
                "name": rel.key,
                "fields": [
                    {"name": col.name, "type": str(col.type)}
                    for col in rel.mapper.columns if col.name != "id"
                ],
                "info": rel.info,  # Include additional info if available
            }

            # Include in relationships only if visible for the given form
            if is_visible(rel.info):
                metadata["relationships"].append(relationship_info)

            # Fetch predefined options for relationships
            if is_visible(rel.info) and rel.info.get("predefined_options", False):
                related_model = rel.mapper.class_
                metadata["predefined_options"][rel.key] = [
                    {"id": obj.unique_ref, "name": getattr(obj, "name", str(obj.unique_ref))}
                    for obj in session.query(related_model).all()
                ]

        return metadata
    
    @staticmethod
    def get_model_by_tablename(tablename: str) -> DeclarativeMeta:
        """Fetch the SQLAlchemy model class by its table name."""
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if hasattr(cls, '__tablename__') and cls.__tablename__ == tablename:
                return cls
        return None


