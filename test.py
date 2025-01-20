@staticmethod
def gather_model_metadata(
    model,
    session: Session,
    form_name: str = None,
    visited_models=None,
    max_depth: int = 2,  # example: limit recursion depth to 2
):
    """
    Gather metadata from the given SQLAlchemy model, optionally recursing 
    into its relationships up to `max_depth` levels deep.

    Args:
        model: SQLAlchemy model class.
        session: SQLAlchemy session for querying related data.
        form_name: The name of the form to filter fields and relationships based on visibility.
        visited_models: A set of (model_class, depth) to avoid infinite loops.
        max_depth: The maximum recursion depth (optional).

    Returns:
        dict: A dictionary containing metadata (columns, form fields, relationships, etc.).
    """

    # 1. Handle initial conditions
    if not model:
        raise ValueError("Model cannot be None.")
    if visited_models is None:
        visited_models = set()  # keep track of visited to avoid loops

    # We can treat "visited" as a combo of (model, depth), or just the model
    # if you only ever want to visit each model class once.
    current_depth = 0
    # If you store depth in visited, you might do something like:
    #   if (model, depth) in visited_models: ...
    # For simplicity, let's do a separate variable to track depth.
    # We'll pass it along but skip if depth > max_depth.

    # 2. Check if we've already visited this model class
    #    If you've got a big web of relationships, you might skip or 
    #    just return a marker (like "Already visited").
    if model in visited_models:
        return {
            "already_visited": True,
            "model_name": model.__name__
        }

    # Mark this model as visited
    visited_models.add(model)

    # Inspect the mapper
    mapper = inspect(model)

    # Build the base metadata dictionary
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

    # Helper to check field/relationship visibility
    def is_visible(info):
        if not form_name:
            return True
        if info and "form_visibility" in info:
            return info["form_visibility"].get(form_name, True)
        return True

    # 3. Gather column metadata
    for column in mapper.columns:
        column_info = {
            "name": column.name,
            "type": str(column.type),
            "options": getattr(model, f"{column.name}_options", None),
            "multi_options": getattr(model, f"{column.name}_multi_options", None),
            "is_foreign_key": bool(column.foreign_keys),
        }
        metadata["columns"].append(column_info)

        # Include in form fields only if visible, skipping unique_ref
        if is_visible(getattr(column, "info", {})) and column.name not in ["unique_ref"]:
            metadata["form_fields"].append(column_info)

    # If "is_request", add some extra columns
    if metadata["is_request"]:
        metadata["columns"].insert(1, {"name": "group_id", "type": "String", "options": None})
        metadata["columns"].insert(1, {"name": "request_status", "type": "String", "options": None})

    # 4. Gather relationships
    #    If we've reached max_depth, we can skip further recursion.
    if max_depth > 0:
        for rel in mapper.relationships:
            # Basic info for the relationship
            relationship_info = {
                "name": rel.key,
                "fields": [
                    {"name": col.name, "type": str(col.type)}
                    for col in rel.mapper.columns
                    if col.name not in ["id", "unique_ref"]
                ],
                "info": rel.info,
            }

            # Check visibility
            if is_visible(rel.info):
                # 4a. Add to the list of relationships
                metadata["relationships"].append(relationship_info)

                # 4b. If `predefined_options` is set, gather them
                if rel.info.get("predefined_options", False):
                    related_model = rel.mapper.class_
                    # e.g., fetch all objects to build an array of { id, name }
                    metadata["predefined_options"][rel.key] = [
                        {
                            "id": obj.unique_ref,
                            "name": getattr(obj, "name", str(obj.unique_ref))
                        }
                        for obj in session.query(related_model).all()
                    ]

                # 4c. **Recursive Call** if you want nested metadata
                #     and if we haven't reached max depth
                if max_depth > 1:
                    related_model = rel.mapper.class_
                    nested_meta = RmsMetadata.gather_model_metadata(
                        model=related_model,
                        session=session,
                        form_name=form_name,
                        visited_models=visited_models,
                        max_depth=max_depth - 1  # reduce depth
                    )
                    # Put the nested metadata inside our relationship_info
                    relationship_info["nested_metadata"] = nested_meta

    # 5. Return the assembled metadata
    return metadata
