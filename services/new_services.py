import csv
from datetime import datetime
import io
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, inspect
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import joinedload

from example_model import Comment, RmsRequest, RmsRequestStatus, User, Base, id_method


class UtilityService:
    @staticmethod
    def transform_rows(rows, model):
        mapper = inspect(model)
        transformed = []
        for row in rows:
            row_data = {col.name: getattr(row, col.name, None) for col in mapper.columns}
            if isinstance(row, tuple):
                model_obj, request_status, group_id = row if len(row) == 3 else (*row, None)
                row_data.update({"request_status": request_status, "group_id": group_id})
            else:
                row_data.update({"request_status": None, "group_id": None})
            transformed.append(row_data)
        return transformed

    @staticmethod
    def fetch_latest_status_subquery(session):
        return (
            session.query(
                RmsRequestStatus.request_id,
                func.max(RmsRequestStatus.timestamp).label("latest_timestamp"),
            )
            .group_by(RmsRequestStatus.request_id)
            .subquery()
        )

    @staticmethod
    def fetch_model_by_name(model_name):
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if hasattr(cls, "__tablename__") and cls.__tablename__ == model_name:
                return cls
        return None


class QueryService:
    @staticmethod
    def fetch_request_data(session):
        subquery = UtilityService.fetch_latest_status_subquery(session)
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
    def fetch_model_data(session, model):
        subquery = UtilityService.fetch_latest_status_subquery(session)
        try:
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
    def fetch_row_by_id(session, model, row_id: int):
        row = session.query(model).filter_by(id=row_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Row not found")
        return row


class CSVService:
    @staticmethod
    def generate_headers_for_model(model):
        mapper = inspect(model)
        headers = [col.name for col in mapper.columns if not col.primary_key]
        for relationship in mapper.relationships:
            headers.extend(
                f"{relationship.key}.{col.name}"
                for col in inspect(relationship.mapper.class_).columns
            )
        return headers

    @staticmethod
    def create_csv_template(headers):
        content = io.StringIO()
        writer = csv.writer(content)
        writer.writerow(headers)
        content.seek(0)
        return content.getvalue()


class AuthorizationService:
    ADMIN_MODELS = {"users"}

    @staticmethod
    def check_access(model_name: str, user: User):
        if model_name in AuthorizationService.ADMIN_MODELS and "Admin" not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin role required to access '{model_name}'. Your roles: {user.roles}",
            )


class ImportService:
    @staticmethod
    def validate_file(file: UploadFile):
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        return file

    @staticmethod
    async def parse_csv(file: UploadFile):
        content = await file.read()
        try:
            csv_reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            return list(csv_reader)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid CSV file format.") from e

    @staticmethod
    def process_row(session, row, model, user, group_id):
        rms_request = RmsRequest(
            requester=user.user_name,
            request_type="RULE DEPLOYMENT",
            group_id=group_id,
        )
        session.add(rms_request)
        session.flush()
        data = {col.name: row[col.name] for col in inspect(model).columns if col.name in row}
        data["rms_request_id"] = rms_request.unique_ref
        session.add(model(**data))

    @staticmethod
    def bulk_import(session, rows, model, user):
        group_id = id_method()
        for row in rows:
            ImportService.process_row(session, row, model, user, group_id)
        session.commit()
        return {"message": "Bulk import completed successfully.", "group_id": group_id}


class BulkUpdateService:
    @staticmethod
    def validate_payload(payload):
        ids, next_status = payload.get("ids"), payload.get("nextStatus")
        if not ids or not next_status:
            raise HTTPException(status_code=400, detail="Invalid request data")
        return ids, next_status

    @staticmethod
    def update_statuses(session, rows, next_status, user):
        for row in rows:
            session.add(
                RmsRequestStatus(
                    request_id=row.RmsRequest.unique_ref,
                    status=next_status,
                    user_name=user.user_name,
                )
            )
        session.commit()
