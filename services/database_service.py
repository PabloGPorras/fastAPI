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
                    RmsRequest,                  # The ORM object
                    RmsRequestStatus,            # The ORM object
                    literal(None).label("group_id")  # Placeholder for group_id
                )
                .join(subquery, RmsRequest.unique_ref == subquery.c.unique_ref)  # Join with subquery
                .all()
            )
        else:
            try:
                rows = (
                    session.query(
                        model,                       # Dynamic model (e.g., RuleConfigRequest)
                        RmsRequestStatus,            # The ORM object
                        RmsRequest  # Fetch group_id from RmsRequest
                    )
                    .join(RmsRequest, model.rms_request_id == RmsRequest.unique_ref)  # Join with RmsRequest
                    .join(RmsRequestStatus, RmsRequest.unique_ref == RmsRequestStatus.unique_ref)  # Join to RmsRequestStatus
                    .join(subquery, RmsRequest.unique_ref == subquery.c.unique_ref)  # Join to find latest status
                    .all()
                )
            except Exception as e:
                logger.error(f"Error during fetch_model_rows: {e}", exc_info=True)
                rows = session.query(model).all()

        return rows

    @staticmethod
    def transform_rows_to_dicts(rows):
        row_dicts = []
        from sqlalchemy.orm import object_mapper

        for row in rows:
            # Now each row has exactly 3 elements
            first_obj, second_obj, third_obj = row

            # Flatten the first object
            flattened = {}
            if first_obj is not None and hasattr(first_obj, '__table__'):
                # It's an ORM object
                for col in object_mapper(first_obj).columns:
                    flattened[col.name] = getattr(first_obj, col.name, None)
            else:
                flattened["object1"] = first_obj  # if it's None or some literal

            # Flatten the second object
            if second_obj is not None and hasattr(second_obj, '__table__'):
                # It's an ORM object, e.g. RmsRequestStatus
                for col in object_mapper(second_obj).columns:
                    flattened[f"status_{col.name}"] = getattr(second_obj, col.name, None)
            else:
                flattened["object2"] = second_obj

            # Flatten the third object
            if third_obj is not None and hasattr(third_obj, '__table__'):
                # Another ORM object, e.g. RmsRequest
                for col in object_mapper(third_obj).columns:
                    flattened[f"rms_{col.name}"] = getattr(third_obj, col.name, None)
            else:
                flattened["object3"] = third_obj

            row_dicts.append(flattened)
        return row_dicts



    @staticmethod
    def _row_to_dict(row):
        """
        Internal method that converts a single row into a dictionary, handling
        different row types:
            - SQLAlchemy Row/RowProxy
            - Single mapped object
            - Tuple of items
            - Plain Python object
        """
        if DatabaseService._is_sa_row(row):
            # SQLAlchemy Row (2.0) or RowProxy (1.x)
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else row._asdict()

        elif DatabaseService._is_mapped_object(row):
            # Single mapped ORM object
            mapper = inspect(row)
            row_dict = {}
            for col in mapper.columns:
                val = getattr(row, col.name, None)
                row_dict[col.name] = DatabaseService._convert_if_datetime(val)

        elif isinstance(row, (tuple, list)):
            # A tuple or list of items (could be a mix of mapped objects, scalars, etc.)
            # We convert each item individually and store them in a list
            row_dict = [DatabaseService._row_to_dict(item) for item in row]

        else:
            # As a fallback, try using the generic Python object approach
            # We'll skip any private/internal attributes
            row_dict = {}
            for attr in dir(row):
                # Skip dunder/magic attributes and private ones
                if not attr.startswith("_"):
                    val = getattr(row, attr, None)
                    # Sometimes these might be methods or descriptors; skip non-values
                    if not callable(val):
                        row_dict[attr] = DatabaseService._convert_if_datetime(val)

            # If that yields nothing, maybe use __dict__ directly (if available)
            if not row_dict and hasattr(row, '__dict__'):
                row_dict = {
                    k: DatabaseService._convert_if_datetime(v) 
                    for k, v in row.__dict__.items() 
                    if not k.startswith("_")
                }

        return row_dict

    @staticmethod
    def _convert_if_datetime(value):
        """
        Convert datetime objects to ISO 8601 string, leave other types unchanged.
        """
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @staticmethod
    def _is_sa_row(item):
        """
        Check if the item is a SQLAlchemy Row / RowProxy (1.x) or Row (2.0).
        """
        # Adjust as needed depending on your SQLAlchemy version
        return isinstance(item, Row) or hasattr(item, '_mapping') or hasattr(item, '_asdict')

    @staticmethod
    def _is_mapped_object(item):
        """
        Check if the item is a SQLAlchemy ORM-mapped object.
        """
        try:
            # If we can retrieve a mapper, it's likely a mapped object.
            inspect(item)
            return True
        except:
            return False

    
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

            # Skip the column entirely if it’s not visible for this form
            if not is_visible(getattr(column, "info", {})):
                continue

            # Also skip if it’s "unique_ref"
            if column.name in ["unique_ref"]:
                continue

            # Otherwise, add it to columns
            metadata["columns"].append(column_info)

            # Potentially add it to form_fields as well
            metadata["form_fields"].append(column_info)

        # Extra columns for "is_request"
        if metadata["is_request"]:
            metadata["columns"].insert(1, {"name": "group_id", "type": "String", "options": None})
            metadata["columns"].insert(1, {"name": "request_status", "type": "String", "options": None})

        # 4) Relationships + recursion
        #    If we've reached 0, skip. Otherwise, go through relationships
        if max_depth > 0:
            for rel in mapper.relationships:
                # Only proceed if visible
                if is_visible(rel.info):
                    # Build minimal relationship info
                    relationship_info = {
                        "name": rel.key,
                        "nested_metadata": {}
                    }

                    # If we still have depth left, recurse
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


