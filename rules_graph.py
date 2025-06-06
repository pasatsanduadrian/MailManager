import networkx as nx
import plotly.graph_objects as go


def rules_to_plot(rules):
    """Returnează o figură Plotly cu relația label-sender."""
    G = nx.Graph()
    for r in rules:
        label = r.get("label")
        senders = r.get("senders", [])
        if not label or not senders:
            continue
        G.add_node(label, type="label")
        for sender in senders:
            sender = str(sender)
            G.add_node(sender, type="sender")
            G.add_edge(sender, label)
    if G.number_of_nodes() == 0:
        return go.Figure()
    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for src, dst in G.edges():
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        mode="lines",
    )
    node_x, node_y, texts = [], [], []
    colors = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        texts.append(node)
        colors.append("#3983E2" if G.nodes[node].get("type") == "label" else "#34a853")
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=texts,
        textposition="top center",
        hoverinfo="text",
        marker=dict(color=colors, size=12, line_width=2),
    )
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20))
    return fig
