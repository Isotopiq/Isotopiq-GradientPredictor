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
    )
    return MultiCompoundSuggestionOut.model_validate(result)


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
    """Create a method from a template."""
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")

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
