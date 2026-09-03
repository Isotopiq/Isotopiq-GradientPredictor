"""Method routes: suggest, CRUD, gradient simulation, chromatogram, templates, sharing."""
from __future__ import annotations

import uuid
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.core.rules.templates import (
    get_categories,
    get_template,
    list_templates,
    template_to_dict,
    template_to_gradient_table,
)
from app.schemas.method import (
    ChromatogramOut,
    ChromatogramRequest,
    GradientSimulateOut,
    GradientSimulateRequest,
    MethodCreate,
    MethodOut,
    MethodSuggestionOut,
    MethodSuggestionRequest,
    MultiCompoundSuggestionRequest,
    MultiCompoundSuggestionOut,
    OptimizeGradientRequest,
    OptimizeGradientOut,
    UserTemplateCreate,
    UserTemplateUpdate,
    UserTemplateOut,
)
from app.services import method_service

router = APIRouter(prefix="/methods", tags=["methods"])


# --- Action routes (no path params, safe to be first) ---


@router.post("/suggest", response_model=MethodSuggestionOut)
async def suggest_method(data: MethodSuggestionRequest) -> MethodSuggestionOut:
    try:
        result = method_service.suggest(data)
    except method_service.MethodServiceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return MethodSuggestionOut.model_validate(result)


@router.post("/gradient/simulate", response_model=GradientSimulateOut)
async def simulate_gradient(data: GradientSimulateRequest) -> GradientSimulateOut:
    result = method_service.simulate_gradient(data)
    return GradientSimulateOut.model_validate(result)


@router.post("/chromatogram", response_model=ChromatogramOut)
async def simulate_chromatogram(data: ChromatogramRequest) -> ChromatogramOut:
    result = method_service.simulate_chromatogram_from_request(data)
    return ChromatogramOut.model_validate(result)


@router.post("/suggest-multi", response_model=MultiCompoundSuggestionOut)
async def suggest_multi_method(data: MultiCompoundSuggestionRequest) -> MultiCompoundSuggestionOut:
    result = method_service.suggest_multi(
        smiles_list=data.smiles_list,
        ionization_mode=data.ionization_mode,
        retention_goal=data.retention_goal,
        gradient_time_min=data.gradient_time_min,
        flow_rate_ml_min=data.flow_rate_ml_min,
        column_type=data.column_type,
    )
    return MultiCompoundSuggestionOut.model_validate(result)


@router.post("/optimize-gradient", response_model=OptimizeGradientOut)
async def optimize_gradient(data: OptimizeGradientRequest) -> OptimizeGradientOut:
    """Grid-search for the gradient parameters that maximize separation."""
    result = method_service.optimize_gradient_separation(
        smiles_list=data.smiles_list,
        flow_rate_ml_min=data.flow_rate_ml_min,
        gradient_time_min=data.gradient_time_min,
        column_type=data.column_type,
        ph=data.ph,
        temperature_c=data.temperature_c,
    )
    return OptimizeGradientOut.model_validate(result)


@router.post("", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def create_method(data: MethodCreate, db: DBSession, current: CurrentUser) -> MethodOut:
    method = await method_service.create_method(db, current.id, data)
    return MethodOut.model_validate(method)


@router.get("", response_model=list[MethodOut])
async def list_methods(
    db: DBSession,
    current: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[MethodOut]:
    items = await method_service.list_methods(db, current.id, limit, offset)
    return [MethodOut.model_validate(m) for m in items]


# --- Static path segments (MUST be before /{method_id}) ---


# --- Method Templates ---

@router.get("/templates/list")
async def list_method_templates(category: str | None = Query(None)) -> list[dict]:
    """List available method templates."""
    templates = list_templates(category)
    return [template_to_dict(t) for t in templates]


@router.get("/templates/categories")
async def list_template_categories() -> list[str]:
    """List template categories."""
    return get_categories()


@router.post("/templates/{template_id}/apply", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def apply_template(
    template_id: str,
    db: DBSession,
    current: CurrentUser,
    name: str | None = Query(None),
) -> MethodOut:
    """Create a method from a template (built-in or user-created)."""
    # First check built-in templates
    template = get_template(template_id)
    if template is not None:
        gradient_table = template_to_gradient_table(template)
        data = MethodCreate(
            name=name or template.name,
            column_type=template.column_type,
            column_dims={
                "length_mm": template.column_length_mm,
                "particle_size_um": template.particle_size_um,
            },
            mobile_phase_a=template.mobile_phase_a,
            mobile_phase_b=template.mobile_phase_b,
            additive=template.additive,
            ph=template.ph,
            gradient_table=gradient_table,
            flow_rate_ml_min=template.flow_rate_ml_min,
            temperature_c=template.temperature_c,
        )
        method = await method_service.create_method(db, current.id, data)
        return MethodOut.model_validate(method)

    # Check user-created templates
    from sqlalchemy import select
    from app.models.user_method_template import UserMethodTemplate
    import uuid as uuid_mod

    try:
        tmpl_uuid = uuid_mod.UUID(template_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")

    stmt = select(UserMethodTemplate).where(UserMethodTemplate.id == tmpl_uuid)
    result = await db.execute(stmt)
    user_tmpl = result.scalar_one_or_none()
    if user_tmpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    if user_tmpl.owner_id != current.id and not user_tmpl.is_shared:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    # Build gradient table from template params
    t_total = user_tmpl.gradient_time_min * 60
    gradient_table = [
        {"time_s": 0, "percent_b": user_tmpl.percent_b_start},
        {"time_s": 60, "percent_b": user_tmpl.percent_b_start},
        {"time_s": t_total - 120, "percent_b": user_tmpl.percent_b_end},
        {"time_s": t_total, "percent_b": user_tmpl.percent_b_end},
    ]
    data = MethodCreate(
        name=name or user_tmpl.name,
        column_type=user_tmpl.column_type,
        column_dims={
            "length_mm": user_tmpl.column_length_mm,
            "particle_size_um": user_tmpl.particle_size_um,
        },
        mobile_phase_a=user_tmpl.mobile_phase_a,
        mobile_phase_b=user_tmpl.mobile_phase_b,
        additive=user_tmpl.additive,
        ph=user_tmpl.ph,
        gradient_table=gradient_table,
        flow_rate_ml_min=user_tmpl.flow_rate_ml_min,
        temperature_c=user_tmpl.temperature_c,
    )
    method = await method_service.create_method(db, current.id, data)
    return MethodOut.model_validate(method)


# --- User-Created Template CRUD ---


@router.get("/templates/user/list", response_model=list[UserTemplateOut])
async def list_user_templates(
    db: DBSession,
    current: CurrentUser,
) -> list[UserTemplateOut]:
    """List user-created templates (own + shared)."""
    from sqlalchemy import select
    from app.models.user_method_template import UserMethodTemplate

    stmt = select(UserMethodTemplate).where(
        (UserMethodTemplate.owner_id == current.id) | (UserMethodTemplate.is_shared == True)
    ).order_by(UserMethodTemplate.created_at.desc())
    result = await db.execute(stmt)
    templates = result.scalars().all()
    return [UserTemplateOut.model_validate(t) for t in templates]


@router.post("/templates/user/create", response_model=UserTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_user_template(
    data: UserTemplateCreate,
    db: DBSession,
    current: CurrentUser,
) -> UserTemplateOut:
    """Create a new user-defined method template."""
    from app.models.user_method_template import UserMethodTemplate

    template = UserMethodTemplate(
        owner_id=current.id,
        name=data.name,
        category=data.category,
        description=data.description,
        column_type=data.column_type,
        mobile_phase_a=data.mobile_phase_a,
        mobile_phase_b=data.mobile_phase_b,
        additive=data.additive,
        ph=data.ph,
        percent_b_start=data.percent_b_start,
        percent_b_end=data.percent_b_end,
        gradient_time_min=data.gradient_time_min,
        flow_rate_ml_min=data.flow_rate_ml_min,
        temperature_c=data.temperature_c,
        column_length_mm=data.column_length_mm,
        particle_size_um=data.particle_size_um,
        is_shared=data.is_shared,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return UserTemplateOut.model_validate(template)


@router.patch("/templates/user/{template_id}", response_model=UserTemplateOut)
async def update_user_template(
    template_id: uuid.UUID,
    data: UserTemplateUpdate,
    db: DBSession,
    current: CurrentUser,
) -> UserTemplateOut:
    """Update an existing user-created template."""
    from sqlalchemy import select
    from app.models.user_method_template import UserMethodTemplate

    stmt = select(UserMethodTemplate).where(UserMethodTemplate.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    if template.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.commit()
    await db.refresh(template)
    return UserTemplateOut.model_validate(template)


@router.delete("/templates/user/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_template(
    template_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
) -> None:
    """Delete a user-created template."""
    from sqlalchemy import select
    from app.models.user_method_template import UserMethodTemplate

    stmt = select(UserMethodTemplate).where(UserMethodTemplate.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    if template.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    await db.delete(template)
    await db.commit()


# --- Method Sharing (public route) ---

@router.get("/shared/{token}", response_model=MethodOut)
async def get_shared_method(token: str, db: DBSession) -> MethodOut:
    """Get a shared method by token (public, no auth required)."""
    from sqlalchemy import select
    from app.models.method import Method

    stmt = select(Method).where(Method.share_token == token)
    result = await db.execute(stmt)
    method = result.scalar_one_or_none()
    if method is None or not method.is_shared:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared method not found")
    return MethodOut.model_validate(method)


# --- Parameterized routes (MUST be last) ---


@router.get("/{method_id}", response_model=MethodOut)
async def get_method(method_id: uuid.UUID, db: DBSession, current: CurrentUser) -> MethodOut:
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id is not None and method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return MethodOut.model_validate(method)


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_method(method_id: uuid.UUID, db: DBSession, current: CurrentUser) -> None:
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    await method_service.delete_method(db, method_id)


@router.post("/{method_id}/share", response_model=MethodOut)
async def share_method(
    method_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> MethodOut:
    """Generate a share token for a method."""
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    method.is_shared = True
    if not method.share_token:
        method.share_token = secrets.token_urlsafe(16)
    await db.commit()
    await db.refresh(method)
    return MethodOut.model_validate(method)


@router.post("/{method_id}/fork", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def fork_method(
    method_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> MethodOut:
    """Copy a method (e.g. a shared one) into the current user's account."""
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")

    data = MethodCreate(
        name=f"{method.name or 'Method'} (copy)",
        column_type=method.column_type,
        column_dims=method.column_dims,
        mobile_phase_a=method.mobile_phase_a,
        mobile_phase_b=method.mobile_phase_b,
        additive=method.additive,
        ph=method.ph,
        gradient_table=method.gradient_table,
        flow_rate_ml_min=method.flow_rate_ml_min,
        temperature_c=method.temperature_c,
    )
    new_method = await method_service.create_method(db, current.id, data)
    return MethodOut.model_validate(new_method)
