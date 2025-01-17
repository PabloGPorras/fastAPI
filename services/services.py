import csv
from datetime import datetime
import io
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, inspect
from sqlalchemy.ext.declarative import DeclarativeMeta

from example_model import Comment, RmsRequest, RmsRequestStatus, User, Base, id_method
from fastapi import status
from sqlalchemy.orm import joinedload, subqueryload


class DataTransformationService:
    @staticmethod
    def transform_rows(rows, model):
        mapper = inspect(model)
        row_dicts = []
        for row in rows:
            row_data = {}
            if isinstance(row, tuple):
                model_obj, request_status, group_id = row if len(row) == 3 else (*row, None)
                for col in mapper.columns:
                    row_data[col.name] = getattr(model_obj, col.name, None)
                row_data["request_status"] = request_status
                row_data["group_id"] = group_id
            else:
                for col in mapper.columns:
                    row_data[col.name] = getattr(row, col.name, None)
                row_data["request_status"] = None
                row_data["group_id"] = None
            row_dicts.append(row_data)
        return row_dicts

    @staticmethod
    def add_relationships(row, model):
        """
        Dynamically add relationships to the row dictionary.
        """
        row_data = DataTransformationService.row_to_dict(row, model)
        for relationship in inspect(model).relationships:
            related_rows = getattr(row, relationship.key)
            row_data[relationship.key] = [
                {column.key: getattr(related_row, column.key) for column in inspect(relationship.mapper.class_).columns}
                for related_row in related_rows
            ]
        return row_data

    @staticmethod
    def extract_columns(model):
        """
        Extract column metadata, including restricted fields and options.
        """
        mapper = inspect(model)
        columns = []
        restricted_fields = getattr(model, "restricted_fields", [])

        for column in mapper.columns:
            column_info = {
                "name": column.name,
                "type": str(column.type),
                "options": getattr(model, f"{column.name}_options", None),
                "multi_options": getattr(model, f"{column.name}_multi_options", None),
                "is_foreign_key": bool(column.foreign_keys),
            }
            columns.append(column_info)

        # Add dynamic fields for `is_request` models
        if getattr(model, "is_request", False):
            columns.insert(0, {"name": "request_status", "type": "String", "options": None})
            columns.insert(1, {"name": "group_id", "type": "String", "options": None})

        return columns
    
class QueryService:
    @staticmethod
    def fetch_request_data(session):
        subquery = (
            session.query(
                RmsRequestStatus.request_id,
                func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
            )
            .group_by(RmsRequestStatus.request_id)
            .subquery()
        )
        return session.query(
            RmsRequest,
            RmsRequestStatus.status.label("request_status"),
        ).join(
            subquery, RmsRequest.unique_ref == subquery.c.request_id
        ).join(
            RmsRequestStatus,
            (RmsRequestStatus.request_id == subquery.c.request_id)
            & (RmsRequestStatus.timestamp == subquery.c.latest_timestamp),
        ).all()

    @staticmethod
    def fetch_model_data(session, model, model_name):
        try:
            subquery = (
                session.query(
                    RmsRequestStatus.request_id,
                    func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
                )
                .group_by(RmsRequestStatus.request_id)
                .subquery()
            )
            return session.query(
                model,
                RmsRequestStatus.status.label("request_status"),
                RmsRequest.group_id.label("group_id"),
            ).join(
                RmsRequest, model.rms_request_id == RmsRequest.unique_ref
            ).join(
                subquery, RmsRequest.unique_ref == subquery.c.request_id
            ).join(
                RmsRequestStatus,
                (RmsRequestStatus.request_id == subquery.c.request_id)
                & (RmsRequestStatus.timestamp == subquery.c.latest_timestamp),
            ).all()
        except Exception:
            return session.query(model).all()

class ModelService:
    @staticmethod
    def get_models_with_is_request():
        """
        Fetch all models where the 'is_request' attribute is True.
        """
        models = []
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if isinstance(cls, DeclarativeMeta) and getattr(cls, "is_request", False):
                models.append({
                    "name": cls.__tablename__.replace("_", " ").capitalize(),
                    "url": f"/{cls.__tablename__}",
                    "model_name": cls.__tablename__,
                })
        return models

    @staticmethod
    def get_model_by_name(model_name: str):
        """
        Get a model by its table name. Raises HTTPException if not found.
        """
        model = ModelService.get_model_by_tablename(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
        return model

    @staticmethod
    def fetch_row_by_id(session, model, row_id: int):
        """
        Fetch a row by ID from the specified model.
        """
        row = session.query(model).filter_by(id=row_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Row not found")
        return row
    
    @staticmethod
    def get_model_by_tablename(tablename: str) -> DeclarativeMeta:
        """
        Fetch the SQLAlchemy model class by its table name.

        :param tablename: Name of the table.
        :return: SQLAlchemy model class or None if not found.
        """
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if hasattr(cls, '__tablename__') and cls.__tablename__ == tablename:
                return cls
        return None



class AuthorizationService:
    ADMIN_MODELS = {"users"}

    @staticmethod
    def check_access(model_name: str, user: User):
        if model_name in AuthorizationService.ADMIN_MODELS and "Admin" not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Admin role required to access '{model_name}'. "
                    f"Your roles: {user.roles}"
                ),
            )


class UpdateService:
    @staticmethod
    def update_row(session, model, row_id: int, data: dict):
        """
        Update a row dynamically based on the model and ID.
        """
        row = ModelService.fetch_row_by_id(session, model, row_id)

        # Update main fields
        for key, value in data.items():
            if key != "relationships" and hasattr(row, key):
                setattr(row, key, value)

        # Update relationships if provided
        relationships = data.get("relationships", {})
        UpdateService.update_relationships(session, row, relationships)

        session.commit()
        return {"message": f"Row with ID {row_id} updated successfully."}

    @staticmethod
    def update_relationships(session, row, relationships: dict):
        """
        Update relationships dynamically for a given row.
        """
        for relationship_name, related_objects in relationships.items():
            if hasattr(row, relationship_name):
                related_attribute = getattr(row, relationship_name)
                related_model = (
                    related_attribute[0].__class__ if related_attribute else None
                )

                if not related_model:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid relationship: {relationship_name}",
                    )

                # Clear existing relationships
                while len(related_attribute) > 0:
                    session.delete(related_attribute.pop())

                # Add new relationships
                for related_object in related_objects:
                    new_related_row = related_model(**related_object)
                    related_attribute.append(new_related_row)


class TemplateService:
    @staticmethod
    def generate_headers_for_model(model):
        """
        Generate headers for the CSV template based on the model's columns and relationships.
        """
        mapper = inspect(model)
        headers = []

        # Add columns that are input-relevant
        for column in mapper.columns:
            if column.primary_key or column.foreign_keys or column.info.get("exclude_from_form", False):
                continue
            headers.append(column.name)

        # Add relationship fields
        for relationship in mapper.relationships:
            if relationship.info.get("exclude_from_form", False):
                continue
            rel_name = relationship.key
            rel_model = relationship.mapper.class_

            # Include fields for the related model
            rel_fields = [
                f"{rel_name}.{column.name}"
                for column in inspect(rel_model).columns
                if not column.primary_key and not column.foreign_keys and not column.info.get("exclude_from_form", False)
            ]
            headers.extend(rel_fields)

        return headers

    @staticmethod
    def create_csv_template(headers):
        """
        Create a CSV template content from headers.
        """
        content = io.StringIO()
        writer = csv.writer(content)
        writer.writerow(headers)  # Write headers
        content.seek(0)
        return content.getvalue()


class ImportService:
    @staticmethod
    def validate_file(file: UploadFile):
        """
        Validate the uploaded file's type and content.
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        return file

    @staticmethod
    async def parse_csv(file: UploadFile):
        """
        Parse the uploaded CSV file into a list of rows.
        """
        content = await file.read()
        try:
            csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            return list(csv_reader)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid CSV file format.") from e

    @staticmethod
    def process_row(session, row: dict, model, user: User, group_id: str):
        """
        Process a single row and insert associated records into the database.
        """
        # Create a new RmsRequest
        rms_request = RmsRequest(
            requester=user.user_name,
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
        session.flush()

        # Insert initial status for the RmsRequest
        initial_status = list(model.request_status_config.keys())[0]  # Get the first status
        rms_status = RmsRequestStatus(
            request_id=rms_request.unique_ref,
            status=initial_status,
            user_name=user.user_name,
        )
        session.add(rms_status)

        # Extract model fields and create the instance
        model_fields = {col.name for col in inspect(model).columns}
        data = {field: row[field] for field in model_fields if field in row}
        data["rms_request_id"] = rms_request.unique_ref  # Associate with RmsRequest

        instance = model(**data)
        session.add(instance)

    @staticmethod
    def bulk_import(session, rows: list, model, user: User):
        """
        Process all rows in the bulk import.
        """
        group_id = id_method()  # Generate a unique group ID
        for row_count, row in enumerate(rows, start=1):
            ImportService.process_row(session, row, model, user, group_id)
        session.commit()
        return {"message": "Bulk import completed successfully!", "group_id": group_id}



class CreationService:
    @staticmethod
    def resolve_and_validate_model(model_name: str):
        """
        Resolve the model by its name and validate its existence.
        """
        model = ModelService.get_model_by_name(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")
        return model

    @staticmethod
    def process_main_fields(data: dict, model):
        """
        Process and filter the main fields for the given model.
        """
        valid_columns = {col.name for col in inspect(model).columns}
        return {key: value for key, value in data.items() if key in valid_columns}

    @staticmethod
    def process_request_model(session, data: dict, model, group_id: str, user: User):
        """
        Handle models with `is_request = True` and create associated records.
        """
        rms_request_data = {
            "unique_ref": data.get("unique_ref"),
            "request_type": data.pop("request_type", model.__tablename__.upper()),
            "effort": data.pop("effort", "Default Effort"),
            "organization": data.pop("organization", "Default Org"),
            "sub_organization": data.pop("sub_organization", "Default Sub Org"),
            "line_of_business": data.pop("line_of_business", "Default LOB"),
            "team": data.pop("team", "Default Team"),
            "decision_engine": data.pop("decision_engine", "Default Engine"),
            "group_id": group_id,
        }

        # Create and flush RmsRequest
        initial_status = list(model.request_status_config.keys())[0]
        new_request = RmsRequest(
            **rms_request_data,
            request_status=initial_status,
        )
        session.add(new_request)
        session.flush()

        # Update data for the main model
        data["unique_ref"] = new_request.unique_ref
        data["rms_request_id"] = new_request.unique_ref

        # Create RmsRequestStatus
        new_status = RmsRequestStatus(
            request_id=new_request.unique_ref,
            status=initial_status,
            user_name=user.user_name,
            timestamp=datetime.utcnow(),
        )
        session.add(new_status)

    @staticmethod
    def handle_relationships(session, main_object, relationships_data: dict, model):
        """
        Dynamically handle relationships for the main object.
        """
        for relationship_name, related_objects in relationships_data.items():
            if hasattr(main_object, relationship_name):
                relationship_attribute = getattr(main_object, relationship_name)
                relationship_model = inspect(model).relationships[relationship_name].mapper.class_

                for related_object in related_objects:
                    related_instance = relationship_model(**related_object)
                    if isinstance(relationship_attribute, list):
                        relationship_attribute.append(related_instance)
                    else:
                        setattr(main_object, relationship_name, related_instance)


class BulkUpdateService:
    @staticmethod
    def validate_payload(payload: dict):
        """
        Validate the payload for required fields.
        """
        ids = payload.get("ids", [])
        current_statuses = payload.get("currentStatuses", [])
        next_status = payload.get("nextStatus")
        request_status_config = payload.get("request_status_config", {})

        if not ids or not next_status:
            raise HTTPException(status_code=400, detail="Invalid request data")
        if not request_status_config:
            raise HTTPException(status_code=400, detail="Request status configuration is missing.")

        return ids, current_statuses, next_status, request_status_config

    @staticmethod
    def fetch_rows(session, ids: list):
        """
        Fetch the latest status for the provided request IDs.
        """
        subquery = (
            session.query(
                RmsRequestStatus.request_id,
                func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
            )
            .filter(RmsRequestStatus.request_id.in_(ids))
            .group_by(RmsRequestStatus.request_id)
            .subquery()
        )

        rows = (
            session.query(RmsRequest, RmsRequestStatus.status)
            .join(subquery, RmsRequest.unique_ref == subquery.c.request_id)
            .join(
                RmsRequestStatus,
                (RmsRequestStatus.request_id == subquery.c.request_id)
                & (RmsRequestStatus.timestamp == subquery.c.latest_timestamp),
            )
            .all()
        )
        return rows

    @staticmethod
    def update_statuses(session, rows, current_statuses, next_status, request_status_config, user: User):
        """
        Perform the status updates for the provided rows.
        """
        updated_count = 0

        for (request, current_status), expected_status in zip(rows, current_statuses):
            if current_status != expected_status:
                continue

            valid_roles = request_status_config.get(current_status, {}).get("Roles", [])
            valid_transitions = request_status_config.get(current_status, {}).get("Next", [])

            user_roles = set(user.roles.split(","))
            if not user_roles.intersection(valid_roles):
                continue

            if next_status in valid_transitions:
                new_status = RmsRequestStatus(
                    request_id=request.unique_ref,
                    status=next_status,
                    user_name=user.user_name,
                )
                session.add(new_status)
                updated_count += 1

        session.commit()
        return updated_count


class DetailsService:
    @staticmethod
    def fetch_item_with_relationships(session, model, item_id: str):
        """
        Fetch an item by its unique reference with all relationships eagerly loaded.
        """
        item = (
            session.query(model)
            .options(joinedload("*"))  # Eagerly load all relationships
            .filter(model.unique_ref == item_id)
            .one_or_none()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item

    @staticmethod
    def transform_item_with_relationships(item, model):
        """
        Transform an item into a dictionary including its relationships.
        """
        # Extract item data
        data = {col.name: getattr(item, col.name) for col in inspect(model).columns}

        # Extract relationships dynamically
        relationships = {}
        for relationship in inspect(model).relationships:
            related_items = getattr(item, relationship.key)
            relationships[relationship.key] = [
                {col.name: getattr(related_item, col.name) for col in relationship.mapper.columns}
                for related_item in (related_items if isinstance(related_items, list) else [related_items])
                if related_item
            ]

        return {"data": data, "relationships": relationships}

class CommentService:
    @staticmethod
    def validate_request_exists(session, unique_ref: str):
        """
        Ensure the RmsRequest exists for the given unique_ref.
        """
        request = session.query(RmsRequest).filter(RmsRequest.unique_ref == unique_ref).one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail=f"Request with unique_ref {unique_ref} does not exist")
        return request

    @staticmethod
    def create_comment(session, unique_ref: str, comment_text: str, user: User):
        """
        Create and save a new comment for the specified RmsRequest.
        """
        new_comment = Comment(
            unique_ref=unique_ref,
            comment=comment_text,
            user_name=user.user_name,
            comment_timestamp=datetime.utcnow(),
        )
        session.add(new_comment)
        session.commit()
        return new_comment

    @staticmethod
    def fetch_comments_for_request(session, unique_ref: str):
        """
        Fetch all comments for a specific RmsRequest identified by unique_ref.
        """
        comments = session.query(Comment).filter(Comment.unique_ref == unique_ref).all()
        return comments

    @staticmethod
    def serialize_comments(comments: list):
        """
        Serialize a list of Comment objects into dictionaries.
        """
        return [
            {
                "comment": comment.comment,
                "user_name": comment.user_name,
                "comment_timestamp": comment.comment_timestamp.isoformat() if comment.comment_timestamp else None,
            }
            for comment in comments
        ]
    

class StatusTransitionService:
    @staticmethod
    def validate_model_and_status_config(model_name: str):
        """
        Validate the model and ensure it has a request status configuration.
        """
        model = ModelService.get_model_by_name(model_name)
        if not model or not hasattr(model, "request_status_config"):
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found or has no status config.")
        return model

    @staticmethod
    def validate_user_permissions(rms_request: RmsRequest, user: User):
        """
        Check if the user's configurations match the request's configurations.
        """
        if not (
            rms_request.organization in user.organizations.split(",") and
            rms_request.sub_organization in user.sub_organizations.split(",") and
            rms_request.line_of_business in user.line_of_businesses.split(",") and
            any(role in user.roles.split(",") for role in ["IMPL", "FS"]) and
            rms_request.decision_engine in user.decision_engines.split(",")
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"User does not have matching configurations for Org: {rms_request.organization}, "
                    f"Sub-Org: {rms_request.sub_organization}, LoB: {rms_request.line_of_business}, "
                    f"Decision Engine: {rms_request.decision_engine}."
                ),
            )

    @staticmethod
    def determine_valid_transitions(current_statuses: list, request_status_config: dict, user_roles: list):
        """
        Determine valid status transitions based on current statuses, the status config, and user roles.
        """
        # Intersect valid transitions for all current statuses
        valid_transitions = set(request_status_config[current_statuses[0]]["Next"])
        for status in current_statuses[1:]:
            if status not in request_status_config:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
            valid_transitions.intersection_update(request_status_config[status]["Next"])

        # Filter transitions by roles
        filtered_transitions = [
            status for status in valid_transitions
            if any(role in user_roles for role in request_status_config.get(status, {}).get("Roles", []))
        ]
        return filtered_transitions
