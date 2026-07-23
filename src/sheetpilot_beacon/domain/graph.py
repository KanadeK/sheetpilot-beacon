"""Cell- and sheet-level dependency graph construction."""

from __future__ import annotations

import networkx as nx

from sheetpilot_beacon.domain.formulas import parse_formula_references
from sheetpilot_beacon.domain.models import WorkbookSnapshot
from sheetpilot_beacon.domain.redaction import redact_sensitive_text


def build_dependency_graph(
    snapshot: WorkbookSnapshot,
    *,
    max_range_cells: int = 10_000,
) -> nx.DiGraph[str]:
    """Build precedent-to-dependent edges for every formula cell."""

    graph: nx.DiGraph[str] = nx.DiGraph(
        filename=snapshot.filename,
        sha256=snapshot.sha256,
    )
    sheet_map = snapshot.sheet_map
    for cell in snapshot.cells:
        graph.add_node(
            cell.node_id,
            sheet=cell.sheet,
            cell=cell.coordinate,
            formula=cell.formula is not None,
            external=False,
            symbolic_range=False,
            visibility=sheet_map[cell.sheet].visibility.value,
        )
    for cell in snapshot.cells:
        if cell.formula is None:
            continue
        references = parse_formula_references(
            cell.formula,
            current_sheet=cell.sheet,
            named_ranges=snapshot.named_range_map,
            max_range_cells=max_range_cells,
        )
        for reference in references:
            if reference.node_id not in graph:
                graph.add_node(
                    reference.node_id,
                    sheet=(
                        f"external:[{reference.external_book}]{reference.sheet}"
                        if reference.external_book
                        else reference.sheet
                    ),
                    cell=reference.coordinate,
                    formula=False,
                    external=reference.external_book is not None,
                    symbolic_range=reference.is_symbolic_range,
                    visibility=(
                        sheet_map[reference.sheet].visibility.value
                        if reference.sheet in sheet_map
                        else None
                    ),
                )
            graph.add_edge(
                reference.node_id,
                cell.node_id,
                token=redact_sensitive_text(reference.token, limit=200),
                external=reference.external_book is not None,
                named_range=reference.named_range,
            )
    return graph


def build_sheet_graph(cell_graph: nx.DiGraph[str]) -> nx.DiGraph[str]:
    """Aggregate cell dependencies into directed worksheet dependencies."""

    graph: nx.DiGraph[str] = nx.DiGraph()
    for source, target in cell_graph.edges:
        source_sheet = str(cell_graph.nodes[source]["sheet"])
        target_sheet = str(cell_graph.nodes[target]["sheet"])
        if graph.has_edge(source_sheet, target_sheet):
            graph[source_sheet][target_sheet]["reference_count"] += 1
        else:
            graph.add_edge(source_sheet, target_sheet, reference_count=1)
    return graph
