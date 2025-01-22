from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, literal
from sqlalchemy.inspection import inspect
from example_model import Base, RmsRequest, RmsRequestStatus
from sqlalchemy.ext.declarative import DeclarativeMeta
import logging
from sqlalchemy.engine import Row


logger = logging.getLogger(__name__)

class DatabaseService:
    @staticmethod
    def fetch_model_rows(
        model_name: str,
        session: Session,
        model,
        filters: dict = None,
        sort_by: str = None,
        sort_order: str = "asc",
    ):
        """
        Fetch rows for a given model dynamically with optional filtering and sorting.

        Args:
            model_name (str): Name of the model/table.
            session (Session): SQLAlchemy session.
            model: SQLAlchemy model class.
            filters (dict): Dictionary of column-value pairs for filtering (optional).
            sort_by (str): Column name to sort by (optional).
            sort_order (str): Sorting order, "asc" or "desc" (default: "asc").

        Returns:
            list: Rows fetched from the database as dictionaries.
        """
        is_request = getattr(model, "is_request", False)

        # Get columns for the main model and related tables
        model_columns = list(model.__table__.columns)  # Get all columns from the model's table
        rms_request_columns = list(RmsRequest.__table__.columns)  # Columns from RmsRequest

        # Define the subquery to get the latest status and its timestamp
        subquery = (
            session.query(
                RmsRequestStatus.unique_ref,
                func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
            )
            .group_by(RmsRequestStatus.unique_ref)
            .subquery()
        )

        # Join the subquery with RmsRequestStatus to get the latest status
        latest_status_query = (
            session.query(
                RmsRequestStatus.unique_ref,
                RmsRequestStatus.status,
                subquery.c.latest_timestamp,
            )
            .join(subquery, (RmsRequestStatus.unique_ref == subquery.c.unique_ref) &
                (RmsRequestStatus.timestamp == subquery.c.latest_timestamp))
            .subquery()
        )

        query = None
        all_columns = []

        # Fetch data based on conditions
        if model_name == "request":
            query = session.query(
                latest_status_query.c.status,
                *rms_request_columns,
            ).join(latest_status_query, RmsRequest.unique_ref == latest_status_query.c.unique_ref)

            all_columns = [latest_status_query.c.status] + rms_request_columns
        elif is_request:
            query = session.query(
                latest_status_query.c.status,
                *model_columns,
                *rms_request_columns,
            ).join(RmsRequest, model.rms_request_id == RmsRequest.unique_ref)\
                .join(latest_status_query, RmsRequest.unique_ref == latest_status_query.c.unique_ref)

            all_columns = [latest_status_query.c.status] + model_columns + rms_request_columns
        else:
            query = session.query(*model_columns)
            all_columns = model_columns

        # Apply filters
        if filters:
            for column, value in filters.items():
                column_attr = getattr(model, column, None)
                if column_attr is None:
                    logger.warning(f"Filter column '{column}' not found in model '{model_name}'.")
                    continue
                query = query.filter(column_attr.like(f"%{value}%"))

        # Apply sorting
        if sort_by:
            sort_column = getattr(model, sort_by, None)
            if sort_column is None:
                logger.warning(f"Sort column '{sort_by}' not found in model '{model_name}'.")
            else:
                if sort_order == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

        rows = query.all()

        # Convert tuples to dictionaries
        row_dicts = [
            dict(zip([col.key if hasattr(col, "key") else col.name for col in all_columns], row))
            for row in rows
        ]

        return row_dicts


    @staticmethod
    def get_all_models_as_dict():
        """
        Returns a dictionary of all models with the model name as the key and the SQLAlchemy class as the value.

        Returns:
            dict: Dictionary mapping model names to SQLAlchemy model classes.
        """
        models_dict = {}
        for mapper in Base.registry.mappers:  # Loop through all registered mappers
            cls = mapper.class_
            if isinstance(cls, DeclarativeMeta):  # Ensure it's a valid SQLAlchemy model
                models_dict[cls.__tablename__] = cls
        return models_dict

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
    def gather_model_metadata(
        model,
        session: Session,
        form_name: str = None,
        visited_models=None,
        max_depth: int = 4  # example: limit recursion depth to 4
    ):
        """
        Gather metadata from the given SQLAlchemy model, optionally recursing 
        into its relationships up to `max_depth` levels deep.

        Args:
            model: SQLAlchemy model class.
            session: SQLAlchemy session for querying related data.
            form_name: The name of the form to filter fields and relationships based on visibility.
            visited_models: A set of models we've already visited to prevent infinite loops.
            max_depth: The maximum recursion depth (optional).

        Returns:
            dict: A dictionary containing metadata (columns, form fields, relationships, etc.).
        """

        # 1) Setup / prevent loops
        if not model:
            raise ValueError("Model cannot be None.")
        if visited_models is None:
            visited_models = set()

        # If we've visited this model class already, return a minimal marker
        if model in visited_models:
            return {
                "already_visited": True,
                "model_name": model.__name__
            }

        # Mark this model as visited
        visited_models.add(model)

        # 2) Inspect model
        mapper = inspect(model)

        metadata = {
            "model_name": model.__name__,
            "columns": [],
            "form_fields": [],
            "relationships": [],
            "predefined_options": {},
            "is_request": getattr(model, "is_request", False),
            "request_menu_category": getattr(model, "request_menu_category", None),
            "request_status_config": getattr(model, "request_status_config", None),
            "checklist_fields": [],  # New attribute for check-list fields
        }

        # Optional helper to check if a field/relationship is visible for this form
        def is_visible(info):
            if not form_name:
                return True
            if info and "form_visibility" in info:
                return info["form_visibility"].get(form_name, True)
            return True

        # 3) Columns + form fields
        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "options": getattr(model, f"{column.name}_options", None),
                "multi_options": getattr(model, f"{column.name}_multi_options", None),
                "is_foreign_key": bool(column.foreign_keys),
            }

            column_visibility = column.info.get("form_visibility", {}) if hasattr(column, "info") else {}

            # Check if the column is for check-list
            if column_visibility.get("check-list", False):
                metadata["checklist_fields"].append(column.name)
                # Assume False for create-new and view-existing
                column_visibility.setdefault("create-new", False)
                column_visibility.setdefault("view-existing", False)

            # Add debugging
            print(f"Inspecting column: {column.name}, visibility: {column_visibility}")

            # Skip the column entirely if it’s not visible for this form
            if not is_visible(column_visibility):
                continue

            # Otherwise, add it to columns
            metadata["columns"].append(column_info)

            # Potentially add it to form_fields as well
            if column.name not in metadata["checklist_fields"] + ["unique_ref"]:
                metadata["form_fields"].append(column_info)

        # Log checklist fields
        print(f"Check-list fields gathered: {metadata['checklist_fields']}")

        # 4) Relationships + recursion
        if max_depth > 0:
            for rel in mapper.relationships:
                if is_visible(rel.info):
                    relationship_info = {
                        "name": rel.key,
                        "nested_metadata": {}
                    }
                    if max_depth > 1:
                        related_model = rel.mapper.class_
                        nested_meta = DatabaseService.gather_model_metadata(
                            model=related_model,
                            session=session,
                            form_name=form_name,
                            visited_models=visited_models,
                            max_depth=max_depth - 1
                        )
                        relationship_info["nested_metadata"] = nested_meta

                    metadata["relationships"].append(relationship_info)

        return metadata



    
    @staticmethod
    def get_model_by_tablename(tablename: str) -> DeclarativeMeta:
        """Fetch the SQLAlchemy model class by its table name."""
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if hasattr(cls, '__tablename__') and cls.__tablename__ == tablename:
                return cls
        return None


