from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from sqlalchemy.ext.declarative import DeclarativeMeta
import logging
from sqlalchemy import select,func, or_
from sqlalchemy.orm import aliased
from database import Base
from list_values import REQUEST_EXTRA_COLUMNS
from models.request import RmsRequest
from models.request_status import RmsRequestStatus
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class DatabaseService:
    @staticmethod
    def get_model_by_request_type(request_type: str):
        """
        Returns the model's __tablename__ for a given request_type.
        
        Args:
            request_type (str): The request type to look up.
        
        Returns:
            str: The __tablename__ of the matching model, or None if not found.
        """
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if isinstance(cls, DeclarativeMeta):
                # Check if the model has a 'request_type' column with predefined options
                request_type_col = getattr(cls, 'request_type', None)
                if request_type_col is not None:
                    column_info = request_type_col.info if hasattr(request_type_col, 'info') else {}
                    options = column_info.get("options", [])

                    # If request_type exists in the model's options, return its tablename
                    if request_type in options:
                        return cls.__tablename__
        return None  # Return None if no matching model is found
    
    @staticmethod
    def fetch_model_rows(
        model_name: str,
        session: Session,
        model,
        filters: Dict[str, Any] = None,  # Column-specific filters
        search_value: str = "",          # Full-table search value
        sort_column_index: Optional[int] = None,
        sort_order: str = "asc",
        start: int = 0,
        length: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch rows for the model with filtering, full-table search, ordering, and pagination.
        For models that are request models (i.e. either model.is_request == True or the model is RmsRequest),
        join the latest Request Status (RmsRequestStatus). Additionally, if model.is_request is True,
        join extra Request data (RmsRequest) to fetch fields like organization and sub_organization.
        Only selected columns (as defined by arrays) are fetched.
        """
        # --- Base setup ---
        base_columns = list(model.__table__.columns)
        base_col_names = [col.name for col in base_columns]
        # Start with the base entities.
        entities = base_columns[:]  # initial list of columns to fetch
        extra_col_names = []        # names for extra columns from joins

        # Define extra columns to fetch.
        request_columns = REQUEST_EXTRA_COLUMNS
        request_status_columns = ["status"]

        # Initialize a dictionary for filtering on extra (joined) columns.
        extra_filters = {}

        if getattr(model, "is_request", False) or (model.__tablename__ == RmsRequest.__tablename__):
            if getattr(model, "is_request", False):
                if hasattr(model, "rms_request"):
                    # Get the related Request model.
                    request_model = model.__mapper__.relationships["rms_request"].mapper.class_
                else:
                    request_model = model

                # Build a list of column attributes from the request_model.
                req_cols = []
                for col in request_columns:
                    col_attr = getattr(request_model, col, None)
                    if col_attr is not None:
                        req_cols.append(col_attr)
                        # Automatically add to extra_filters.
                        extra_filters[col] = col_attr
                        # If you need to track extra column names (for example, for later use)
                        extra_col_names.append(col)

                # Add the extra request columns to your query entities.
                entities.extend(req_cols)
            else:
                request_model = model


            # --- Always join the latest status in this case ---
            latest_status = aliased(RmsRequestStatus)
            correlated_subq = (
                select(func.max(RmsRequestStatus.timestamp))
                .filter(RmsRequestStatus.unique_ref == request_model.__table__.c.unique_ref)
                .scalar_subquery()
            )
            rs_cols = [func.coalesce(getattr(latest_status, col), "").label(col)
                    for col in request_status_columns]
            extra_col_names.extend(request_status_columns)
            entities.extend(rs_cols)
            extra_filters["status"] = getattr(latest_status, "status", None)

            # Build the query: select the entities and apply the necessary joins.
            query = session.query(*entities)
            if getattr(model, "is_request", False) and hasattr(model, "rms_request"):
                query = query.join(model.rms_request)
            query = query.outerjoin(
                latest_status,
                (latest_status.unique_ref == request_model.__table__.c.unique_ref) &
                (latest_status.timestamp == correlated_subq)
            )
        else:
            # For models that are not request models, query the base table only.
            query = session.query(*entities)

        # --- Global search filtering ---
        if search_value:
            search_filters = [
                getattr(model, col.name).ilike(f"%{search_value}%")
                for col in model.__table__.columns
                if hasattr(model, col.name)
                and hasattr(getattr(model, col.name), "type")
                and getattr(model, col.name).type.python_type == str
            ]
            if search_filters:
                query = query.filter(or_(*search_filters))

        # --- Column-specific filtering ---
        if filters:
            for col_name, filter_value in filters.items():
                # Try to get the column from the base model.
                col_attr = getattr(model, col_name, None)
                # If not found and this is a request model, try extra_filters.
                if col_attr is None and (getattr(model, "is_request", False) or (model.__tablename__ == RmsRequest.__tablename__)):
                    col_attr = extra_filters.get(col_name)
                if col_attr is not None:
                    query = query.filter(col_attr == filter_value)

        # --- Count records after filtering ---
        filtered_count = query.count()

        # --- Sorting ---
        if sort_column_index is not None:
            model_columns = list(model.__table__.columns)
            if 0 <= sort_column_index < len(model_columns):
                sort_column = model_columns[sort_column_index]
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

        # --- Pagination ---
        query = query.offset(start).limit(length)
        rows = query.all()

        # Debug: Print shape of returned rows.
        for i, row in enumerate(rows):
            if not isinstance(row, tuple):
                row_tuple = (row,)
            else:
                row_tuple = row
            print(f"Row {i} tuple length: {len(row_tuple)}; values: {row_tuple}")

        # --- Convert rows (tuples) to dictionaries ---
        result = []
        total_base = len(base_columns)
        total_extra = len(extra_col_names)
        for row in rows:
            row = list(row)
            base_data = dict(zip(base_col_names, row[:total_base]))
            extra_data = dict(zip(extra_col_names, row[total_base:])) if total_extra > 0 else {}
            row_dict = {**base_data, **extra_data}
            result.append(row_dict)

        return result, filtered_count










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
                frontend_table_name = getattr(cls, "frontend_table_name", "")
                
                models_with_metadata.append({
                    "name": cls.__tablename__.replace("_", " ").capitalize(),
                    "url": f"/{cls.__tablename__}",
                    "model_name": cls.__tablename__,
                    "is_request": is_request,
                    "request_menu_category": request_menu_category,
                    "frontend_table_name": frontend_table_name
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
        logger.info(f"Fetching data for model: {model}")

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
            "frontend_table_name": getattr(model, "frontend_table_name", None),
            "request_status_config": getattr(model, "request_status_config", None),
            "checklist_fields": [],  # New attribute for check-list fields
        }

        # 3) Columns + form fields
        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "is_foreign_key": bool(column.foreign_keys),
                "model_name": model.__name__,
            }

            # Extract additional metadata from column.info
            column_info["column_options"] = column.info.get("options") if hasattr(column, "info") else None
            column_info["length"] = column.info.get("length", None) if hasattr(column, "info") else None
            column_info["field_name"] = column.info.get("field_name", None) if hasattr(column, "info") else None
            column_info["multi_select"] = column.info.get("multi_select", False) if hasattr(column, "info") else False
            column_info["required"] = column.info.get("required", False) if hasattr(column, "info") else False
            column_info["search"] = column.info.get("search", False) if hasattr(column, "info") else False

            # Check for "forms" key and its nested "enabled" property
            forms_info = column.info.get("forms", {}) if hasattr(column, "info") else {}
            column_info["forms"] = {
                form: {"enabled": form_data.get("enabled", False)} for form, form_data in forms_info.items()
            }

            # Respect the "forms" key in column.info
            if form_name and form_name in forms_info:
                metadata["form_fields"].append(column_info)

            # Add to columns
            metadata["columns"].append(column_info)

        # 4) One-to-Many Relationships + Recursion
        if max_depth > 0:
            for rel in mapper.relationships:
                # Only include one-to-many relationships
                if rel.direction.name == "ONETOMANY":
                    relationship_info = {
                        "name": rel.key,
                        "target_model": rel.mapper.class_.__name__,
                        "nested_metadata": {},
                    }
                    if max_depth > 1:
                        related_model = rel.mapper.class_
                        nested_meta = DatabaseService.gather_model_metadata(
                            model=related_model,
                            session=session,
                            form_name=form_name,
                            visited_models=visited_models,
                            max_depth=max_depth - 1,
                        )
                        relationship_info["nested_metadata"] = nested_meta

                    metadata["relationships"].append(relationship_info)

        return metadata


    @staticmethod
    def get_model_by_tablename(table_name: str):
        logger.debug(f"Looking up model for table name: {table_name}")
        for cls in Base.__subclasses__():
            logger.debug(f"Checking model: {cls.__name__} with table name: {cls.__tablename__}")
            if cls.__tablename__ == table_name.lower():
                logger.info(f"Model found: {cls.__name__}")
                return cls
        logger.warning(f"No model found for table name: {table_name}")
        return None
