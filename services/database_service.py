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
from features.status.models.request_status import RmsRequestStatus
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
            
            # Skip the RmsRequest model
            if cls.__name__ == "RmsRequest":
                continue  

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
    def build_columns_mapping(model) -> Tuple[Dict[str, Any], List[str], List[Any]]:
        """
        Build a mapping of column names to column objects, an ordered list of column names,
        and a list of entities (columns) to select.
        """
        base_columns = {col.name: col for col in model.__table__.columns}
        column_order = list(base_columns.keys())
        entities = list(base_columns.values())
        return base_columns, column_order, entities

    @staticmethod
    def apply_request_joins(query, model, base_columns: Dict[str, Any], 
                            column_order: List[str], entities: List[Any]):
        if getattr(model, "is_request", False) or (model.__tablename__ == RmsRequest.__tablename__):
            if getattr(model, "is_request", False) and hasattr(model, "rms_request"):
                request_model = model.__mapper__.relationships["rms_request"].mapper.class_
            else:
                request_model = model

            for col_name in REQUEST_EXTRA_COLUMNS:
                col_attr = getattr(request_model, col_name, None)
                if col_attr is not None:
                    base_columns[col_name] = col_attr
                    # Replace in entities and column_order only if not already present
                    if col_attr not in entities:
                        entities.append(col_attr)
                    if col_name not in column_order:
                        column_order.append(col_name)

            latest_status = aliased(RmsRequestStatus)
            correlated_subq = (
                select(func.max(RmsRequestStatus.timestamp))
                .filter(RmsRequestStatus.unique_ref == request_model.__table__.c.unique_ref)
                .scalar_subquery()
            )
            status_col = func.coalesce(latest_status.status, "").label("status")
            entities.append(status_col)
            base_columns["status"] = status_col
            column_order.append("status")

            query = query.join(model.rms_request) if getattr(model, "is_request", False) and hasattr(model, "rms_request") else query
            query = query.outerjoin(
                latest_status,
                (latest_status.unique_ref == request_model.__table__.c.unique_ref)
                & (latest_status.timestamp == correlated_subq)
            )
            # **Update the query's selected columns**
            query = query.with_entities(*entities)
        return query, base_columns, column_order, entities

    @staticmethod
    def apply_global_search(query, base_columns: Dict[str, Any], search_value: str, model) -> Any:
        """
        Apply global search filtering across all string columns.
        """
        if search_value:
            search_filters = []
            for name, col in base_columns.items():
                try:
                    # Only apply search to columns with python_type == str
                    if col.type.python_type == str:
                        search_filters.append(col.ilike(f"%{search_value}%"))
                except Exception:
                    continue
            if search_filters:
                query = query.filter(or_(*search_filters))
        return query

    @staticmethod
    def apply_column_filters(query, base_columns: Dict[str, Any], filters: Dict[str, Any]) -> Any:
        """
        Apply column-specific filters based on a mapping of column names to column objects.
        """
        if filters:
            for col_name, filter_value in filters.items():
                col_attr = base_columns.get(col_name)
                if col_attr is not None:
                    query = query.filter(col_attr == filter_value)
        return query

    @staticmethod
    def apply_sorting(query, base_columns: Dict[str, Any], column_order: List[str],
                    sort_column: Optional[str], sort_column_index: Optional[int], sort_order: str) -> Any:
        """
        Apply sorting to the query using either a column name or index.
        """
        # If no sort_column name is provided, try mapping from the column index.
        if not sort_column and sort_column_index is not None:
            if 0 <= sort_column_index < len(column_order):
                sort_column = column_order[sort_column_index]
        if sort_column:
            col_attr = base_columns.get(sort_column)
            if col_attr is not None:
                query = query.order_by(
                    col_attr.desc() if sort_order.lower() == "desc" else col_attr.asc()
                )
        return query

    @staticmethod
    def convert_rows_to_dict(rows, column_order: List[str]) -> List[Dict[str, Any]]:
        results = []
        for row in rows:
            # If row is a SQLAlchemy Row object, use its _mapping attribute.
            if hasattr(row, "_mapping"):
                row_dict = dict(row._mapping)
            else:
                # Fallback: if row is a tuple, convert using column_order.
                row_dict = {name: value for name, value in zip(column_order, row)}
            results.append(row_dict)
        return results

    @staticmethod
    def fetch_model_rows(
        model_name: str,
        session: Session,
        model,
        filters: Dict[str, Any] = None,  # Column-specific filters
        search_value: str = "",          # Full-table search value
        sort_column: Optional[str] = None,
        sort_column_index: Optional[int] = None,
        sort_order: str = "asc",
        start: int = 0,
        length: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch rows for the model with filtering, full-table search, ordering, and pagination.
        
        For request models (model.is_request == True or model is RmsRequest), join extra Request data
        (from RmsRequest and the latest RmsRequestStatus) to include fields such as organization,
        sub_organization, and status.
        """
        # Build the base columns mapping and entity list.
        base_columns, column_order, entities = DatabaseService.build_columns_mapping(model)
        print("DEBUG: Initial column_order:", column_order)

        # Build the initial query.
        query = session.query(*entities)
        # print('______________________________________________________')
        # print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        # If applicable, add request-specific joins and extra columns.
        query, base_columns, column_order, entities = DatabaseService.apply_request_joins(query, model, base_columns, column_order, entities)
        # print('______________________________________________________')
        # print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        print("DEBUG: Updated column_order:", column_order)
        # Apply global search filtering.
        query = DatabaseService.apply_global_search(query, base_columns, search_value, model)
        # print('______________________________________________________')
        # print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        # Apply column-specific filtering.
        query = DatabaseService.apply_column_filters(query, base_columns, filters)
        # print('______________________________________________________')
        # print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        # Count records after filtering.
        filtered_count = query.count()
        
        # Apply sorting.
        query = DatabaseService.apply_sorting(query, base_columns, column_order, sort_column, sort_column_index, sort_order)
        # print('______________________________________________________')
        # print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        # Apply pagination.
        query = query.offset(start).limit(length)
        print('______________________________________________________')
        print(query.statement.compile(compile_kwargs={"literal_binds": True}))


        rows = query.all()
        
        # Convert rows to dictionaries.
        results = DatabaseService.convert_rows_to_dict(rows, column_order)
        
        return results, filtered_count











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
        # logger.info(f"Fetching data for model: {model}")

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
            "is_request": getattr(model, "is_request", False),
            "request_menu_category": getattr(model, "request_menu_category", None),
            "frontend_table_name": getattr(model, "frontend_table_name", None),
            "request_status_config": getattr(model, "request_status_config", None),
            "checklist_fields": [],  # New attribute for check-list fields
        }

        # Extract form config from model
        form_config = getattr(model, "form_config", {})
        field_config_map = {}
        if form_name and form_config.get(form_name, {}).get("enabled", False): # for even disabled
            for field in form_config[form_name].get("fields", []):
                if "field" in field:
                    field_config_map[field["field"]] = field

        # 3) Columns + form fields
        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "is_foreign_key": bool(column.foreign_keys),
                "model_name": model.__name__,
            }

            field_cfg = field_config_map.get(column.name, {})

            #Override fields from form_config
            column_info["field_name"] = field_cfg.get("field_name", column.name)
            column_info["multi_select"] = field_cfg.get("multi_select", False)
            column_info["required"] = field_cfg.get("required", False)
            column_info["column_options"] = column.info.get("options") if hasattr(column, "info") else None
            column_info["visibility"] = field_cfg.get("visibility", [])
            column_info["search_config"] = {
                "enabled": field_cfg.get("search", False),
                "predefined_conditions": field_cfg.get("predefined_conditions", [])
            }

            # Add to columns
            metadata["columns"].append(column_info)

            if form_name and column.name in field_config_map:
                metadata["form_fields"].append(column_info)

        # 4) One-to-Many Relationships + Recursion
        if max_depth > 0:
            for rel in mapper.relationships:
                # Only include one-to-many relationships
                if rel.direction.name == "ONETOMANY":
                    relationship_info = {
                        "name": rel.key,
                        "target_model": rel.mapper.class_.__name__,
                        "nested_metadata": {},
                        "search_config": {
                            "enabled": False,
                            "predefined_conditions": []
                        }
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
    def  get_model_by_tablename(table_name: str):
        for cls in Base.__subclasses__():
            if cls.__tablename__ == table_name.lower():
                logger.info(f"Model found: {cls.__name__}")
                return cls
        return None
