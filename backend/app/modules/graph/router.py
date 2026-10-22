"""HTTP LAYER for the shared knowledge graph."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app import endpoints as ep
from app.core.responses import Envelope, ok
from app.modules.auth import CurrentUserId
from app.modules.graph.dependencies import get_graph_service
from app.modules.graph.schemas import MyGraphOut, NodeDetailOut, NodeOut, PathsOut
from app.modules.graph.service import GraphService

router = APIRouter(tags=["graph"])

Service = Annotated[GraphService, Depends(get_graph_service)]


@router.get(ep.GRAPH_ME, response_model=Envelope[MyGraphOut])
async def my_graph(user_id: CurrentUserId, service: Service) -> Envelope[MyGraphOut]:
    return ok(await service.me(user_id))


@router.get(ep.GRAPH_NODE, response_model=Envelope[NodeDetailOut])
async def graph_node(
    kind: str, key: str, _: CurrentUserId, service: Service
) -> Envelope[NodeDetailOut]:
    return ok(await service.node(kind, key))


@router.get(ep.GRAPH_SEARCH, response_model=Envelope[list[NodeOut]])
async def graph_search(
    _: CurrentUserId,
    service: Service,
    q: Annotated[str, Query(min_length=1, max_length=80)],
    kind: Annotated[str | None, Query()] = None,
) -> Envelope[list[NodeOut]]:
    return ok(await service.search(q, kind))


@router.get(ep.GRAPH_PATHS, response_model=Envelope[PathsOut])
async def graph_paths(
    _: CurrentUserId,
    service: Service,
    role: Annotated[str, Query(min_length=1, max_length=120)],
) -> Envelope[PathsOut]:
    return ok(await service.paths(role))
