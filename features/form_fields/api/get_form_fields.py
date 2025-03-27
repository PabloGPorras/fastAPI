from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from core.get_db_session import get_db_session
from core.templates import templates
from services.database_service import DatabaseService
from database import logger
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

@router.post("/get-form-fields", response_class=HTMLResponse)
async def get_form_fields(
    request: Request,
    model_name: str,
    form_name: str,
    unique_ref: Optional[str] = None,
    status: Optional[str] = None,
    user_roles: Optional[str] = None,
    session: Session = Depends(get_db_session)
):
    try:
        logger.info("get-form-fields called with:")
        logger.info(f"model_name: {model_name}")
        logger.info(f"form_name: {form_name}")
        logger.info(f"unique_ref: {unique_ref}")
        logger.info(f"status: {status}")
        logger.info(f"user_roles raw: {user_roles}")

        role_list = [r.strip() for r in user_roles.split(',')] if user_roles else []
        logger.info(f"Parsed role_list: {role_list}")

        model = DatabaseService.get_model_by_tablename(model_name)
        if not model:
            logger.warning(f"Model '{model_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        form_config = getattr(model, "form_config", {}).get(form_name, {})
        if not form_config:
            logger.warning(f"No form config found for '{form_name}' in model '{model_name}'")
        else:
            logger.info(f"Form config for '{form_name}': {form_config}")
        form_enabled = form_config.get("enabled", False)
        field_groups = form_config.get("field_groups", [])

        if not field_groups:
            logger.warning(f"No field_groups defined for '{form_name}'")

        existing_data = {}
        if unique_ref:
            item = session.query(model).filter_by(unique_ref=unique_ref).one_or_none()
            if not item:
                logger.warning(f"No item found with unique_ref '{unique_ref}'")
                raise HTTPException(status_code=404, detail=f"Item not found for unique_ref '{unique_ref}'")

            # Start with the model's own fields
            existing_data = {
                column.name: getattr(item, column.name, None)
                for column in model.__table__.columns
            }

            # Inject request_type from the related RmsRequest if present
            if hasattr(item, "rms_request") and item.rms_request:
                existing_data["request_type"] = item.rms_request.request_type


        grouped_fields = []
        for group in field_groups:
            group_name = group.get("group_name", "")
            group_edit_conditions = group.get("edit_conditions", {})
            group_allowed_roles = group_edit_conditions.get("allowed_roles", [])
            group_allowed_states = group_edit_conditions.get("allowed_states", [])

            if not group_edit_conditions:
                group_enabled = form_enabled
                logger.info(f"Group '{group_name}' has no edit conditions. Using form_enabled: {form_enabled}")
            else:
                group_allows_edit = not group_allowed_roles or any(role in group_allowed_roles for role in role_list)
                group_state_allows_edit = not group_allowed_states or (status in group_allowed_states if status else False)
                group_enabled = group_allows_edit and group_state_allows_edit

                logger.info(f"Group '{group_name}' enabled: {group_enabled}")
                logger.info(f" |- Form Enabled: {form_enabled}")
                logger.info(f" |- Edit Conditions: {group_edit_conditions}")
                logger.info(f" |  - Allowed Roles: {group_allowed_roles}")
                logger.info(f" |  - User Roles: {role_list}")
                logger.info(f" |  - Role Match: {group_allows_edit}")
                logger.info(f" |  - Allowed States: {group_allowed_states}")
                logger.info(f" |  - Current Status: {status}")
                logger.info(f" |  - State Match: {group_state_allows_edit}")

            fields_config = group.get("fields", [])
            group_obj = {
                "group_name": group_name,
                "fields": []
            }

            for cfg in fields_config:
                field_name = cfg["field"]
                try:
                    column = getattr(model, field_name).property.columns[0]
                except Exception as e:
                    logger.warning(f"Could not access column '{field_name}' on model '{model_name}': {e}")
                    continue

                visibility_conditions = cfg.get("visibility", [])

                field_info = {
                    "name": field_name,
                    "display_name": cfg.get("field_name", field_name.replace("_", " ").title()),
                    "type": str(column.type),
                    "options": cfg.get("options", []),
                    "multi_select": cfg.get("multi_select", False),
                    "required": cfg.get("required", False),
                    "enabled": group_enabled,
                    "visibility_conditions": visibility_conditions,
                    "required_if_visible": cfg.get("required_if_visible", True),
                    "max_length": getattr(column.type, "length", None),
                    "value": existing_data.get(field_name, "") if unique_ref else ""
                }

                test= field_info["required"]
                print(f"Field info for '{field_name}': {test}")
                # Add search configuration from cfg.
                if "search_config" in cfg:
                    field_info["search_config"] = {
                        "enabled": cfg["search_config"].get("enabled", False),
                        "predefined_conditions": cfg["search_config"].get("predefined_conditions", [])
                    }
                else:
                    field_info["search_config"] = {"enabled": False, "predefined_conditions": []}

                group_obj["fields"].append(field_info)

            grouped_fields.append(group_obj)

        if not grouped_fields:
            logger.warning(f"No fields returned for form '{form_name}' on model '{model_name}'")

        return templates.TemplateResponse("form_fields.html", {
            "request": request,
            "grouped_fields": grouped_fields,
            "form_name": form_name,
            "model_name": model_name
        })

    except HTTPException as e:
        logger.warning(f"HTTP error: {e.detail}")
        return HTMLResponse(f"Error: {e.detail}", e.status_code)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return HTMLResponse(f"Unexpected error: {str(e)}", 500)