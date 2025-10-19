from app.adapters.graph.neo4j_client import run_query

def sync_startup_to_graph(startup):
    q = """
    MERGE (s:Startup {name: $name})
    SET s.sector = $sector, s.stage = $stage, s.geo = $geo
    """
    run_query(q, startup)