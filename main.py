import networkx as nx
import pandas as pd
from dash import html
from dash.dependencies import Input, Output

from app import app
from datasets import mock_data
from viz import (
    display_network,
    display_table,
    graph_edges,
    graph_nodes,
    split_filter_part,
    unpack_edges,
    unpack_nodes,
)

COLUMNS = [
    "voter_id",
    "first_name",
    "last_name",
    "phone",
    "precinct",
    "support",
    "gender",
]

if __name__ == "__main__":
    nodes, edges, network = mock_data()
    tall = edges.merge(nodes, left_on="source", right_on="voter_id", how="left")
    tall = tall.merge(
        nodes,
        left_on="target",
        right_on="voter_id",
        suffixes=("_source", "_target"),
        how="left",
    )

    nodes["color"] = nodes["support"].map(
        {
            "5 - Oppose": "#db231d",
            "4 - Lean Oppose": "#e97b77",
            "3 - Undecided": "#b094b0",
            "2 - Lean Support": "#77ace9",
            "1 - Support": "#1d76db",
        }
    )
    full_edge_trace = graph_edges(*unpack_edges(network), ids=nodes["voter_id"])
    text = nodes["first_name"] + " " + nodes["last_name"]
    node_positions = unpack_nodes(network)
    full_node_trace = graph_nodes(
        x=node_positions["x"],
        y=node_positions["y"],
        z=node_positions["z"],
        node_colors=nodes["color"],
        node_text=text,
        ids=nodes["voter_id"],
    )

    app.layout = html.Div(
        [
            html.H1("Network Visualizer", className="header"),
            html.Div(
                [display_network(full_edge_trace, full_node_trace)],
                className="graph-container",
                id="graph-viz",
            ),
            html.Div(
                [
                    html.H3("Search", id="search-title"),
                    html.P(
                        """
                        Quote spaces in your filter, e.g.
                        search "1 - Support" and not 1 - Support
                        """
                    ),
                    display_table(
                        df=nodes[COLUMNS],
                        columns=COLUMNS,
                        html_id="search",
                        search=True,
                    ),
                ],
                className="table-wide",
            ),
            html.Div(
                [
                    html.H3("Source", id="source-title"),
                    display_table(df=nodes[COLUMNS], columns=COLUMNS, html_id="source"),
                ],
                className="table-wide",
            ),
            html.Div(
                [
                    html.H3("Target", id="target-title"),
                    display_table(df=nodes[COLUMNS], columns=COLUMNS, html_id="target"),
                ],
                className="table-wide",
            ),
        ]
    )

    @app.callback(
        Output("description", "data"),
        [Input("description", "filter_query")],
        supress_callback_exceptions=True,
    )
    def update_table(filter):
        filtering_expressions = filter.split(" && ")
        dff = tall
        for filter_part in filtering_expressions:
            col_name, operator, filter_value = split_filter_part(filter_part)
            if operator in ("eq", "ne", "lt", "le", "gt", "ge"):
                # these operators match pandas series operator method names
                dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
            elif operator == "contains":
                dff = dff.loc[dff[col_name].str.contains(filter_value)]
            elif operator == "datestartswith":
                # this is a simplification of the front-end filtering logic,
                # only works with complete fields in standard format
                dff = dff.loc[dff[col_name].str.startswith(filter_value)]
        return dff.to_dict("records")

    @app.callback(Output("search", "data"), [Input("search", "filter_query")])
    def update_names(filter):
        id_field = "voter_id"
        filtering_expressions = filter.split(" && ")
        dff = nodes.sort_values(id_field)
        for filter_part in filtering_expressions:
            col_name, operator, filter_value = split_filter_part(filter_part)
            if operator in ("eq", "ne", "lt", "le", "gt", "ge"):
                # these operators match pandas series operator method names
                dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
            elif operator == "contains":
                dff = dff.loc[dff[col_name].str.contains(filter_value)]
            elif operator == "datestartswith":
                # this is a simplification of the front-end filtering logic,
                # only works with complete fields in standard format
                dff = dff.loc[dff[col_name].str.startswith(filter_value)]
        return dff.to_dict("records")

    # Update the source data table
    @app.callback(
        Output("network", "selectedData"),
        [Input("description", "filter_query")],
    )
    def update_source_table(filter):
        filtering_expressions = filter.split(" && ")
        dff = tall
        for filter_part in filtering_expressions:
            col_name, operator, filter_value = split_filter_part(filter_part)
            if operator in ("eq", "ne", "lt", "le", "gt", "ge"):
                # these operators match pandas series operator method names
                dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
            elif operator == "contains":
                dff = dff.loc[dff[col_name].str.contains(filter_value)]
            elif operator == "datestartswith":
                # this is a simplification of the front-end filtering logic,
                # only works with complete fields in standard format
                dff = dff.loc[dff[col_name].str.startswith(filter_value)]
        return dff["voter_id_target"].tolist()

    @app.callback(
        Output("source", "data"),
        [Input("search", "active_cell"), Input("search", "data")],
    )
    def update_sources(
        selection,
        data,
        id_field="voter_id",
        target_field="target",
        source_field="source",
    ):
        if selection:
            # Get occurrences of name in the source file
            row_index = selection["row"]
            person_id = data[row_index][id_field]

            # The people this person sourced
            source_names = edges[edges[source_field] == person_id][
                target_field
            ].tolist()
            sources = nodes[nodes[id_field].isin(source_names)]
            return sources[COLUMNS].to_dict("records")
        else:
            return nodes[COLUMNS].to_dict("records")

    # Update the target data table
    @app.callback(
        Output("target", "data"),
        [Input("search", "active_cell"), Input("search", "data")],
    )
    def update_targets(
        selection,
        data,
        id_field="voter_id",
        target_field="target",
        source_field="source",
    ):
        if selection:
            # Get occurrences of name in the source file
            row_index = selection["row"]
            person_id = data[row_index][id_field]

            # The people who sourced this person
            target_names = edges[edges[target_field] == person_id][
                source_field
            ].tolist()
            targets = nodes[nodes[id_field].isin(target_names)]
            return targets[COLUMNS].to_dict("records")
        else:
            return nodes[COLUMNS].to_dict("records")

    @app.callback(
        Output("graph-viz", "children"),
        [Input("search", "active_cell"), Input("search", "data")],
    )
    def update_network(selection, data, id_field="voter_id"):
        if selection:
            row_index = selection["row"]
            person_id = data[row_index][id_field]
            subgraph = nx.subgraph_view(
                network,
                filter_edge=lambda source, target: source == person_id
                or target == person_id,
            )
            filtered_edges = pd.DataFrame(subgraph.edges, columns=["source", "target"])
            selected_ids = set(
                filtered_edges.source.tolist() + filtered_edges.target.tolist()
            )

            filtered_nodes = nodes[nodes.voter_id.isin(selected_ids)].reset_index(
                drop=True
            )
            edge_trace = graph_edges(
                *unpack_edges(subgraph), ids=filtered_nodes["voter_id"]
            )
            positions = unpack_nodes(subgraph, filtered_nodes.voter_id.unique())
            node_trace = graph_nodes(
                x=positions["x"],
                y=positions["y"],
                z=positions["z"],
                node_colors=filtered_nodes["color"],
                node_text=filtered_nodes["first_name"]
                + " "
                + filtered_nodes["last_name"],
                ids=filtered_nodes["voter_id"],
            )

            return display_network(edge_trace, node_trace, filtered=True)
        else:
            return display_network(full_edge_trace, full_node_trace, filtered=False)

    # Update the target header
    @app.callback(
        Output("target-title", "children"),
        [Input("search", "active_cell"), Input("search", "data")],
    )
    def update_target_header(
        selection,
        data,
        id_field="voter_id",
        print_fields=["first_name", "last_name"],
    ):
        if selection:
            # Get occurrences of name in the source file
            row_index = selection["row"]
            name = " ".join(data[row_index][x] for x in print_fields)
            return f"{name} contacted these people..."
        else:
            return "Target"

    # Update the source header
    @app.callback(
        Output("source-title", "children"),
        [Input("search", "active_cell"), Input("search", "data")],
    )
    def update_source_header(
        selection,
        data,
        id_field="voter_id",
        print_fields=["first_name", "last_name"],
    ):
        if selection:
            # Get occurrences of name in the source file
            row_index = selection["row"]
            name = " ".join(data[row_index][x] for x in print_fields)
            return f"These people contacted {name}..."
        else:
            return "Source"

    app.run_server(host="0.0.0.0", debug=True)
