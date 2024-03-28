import networkx as nx
import random
from pyvis.network import Network
import webbrowser
from neo4j import GraphDatabase


# Neo4j connection parameters
uri = "bolt://localhost:7689"
user = "neo4j"
password = "abcd1234"


# Define the supply chain graph
G = nx.DiGraph()

# Add nodes (locations)
locations = ['Factory A', 'Factory B', 'Warehouse A', 'Warehouse B', 'Warehouse C', 'Warehouse D',
             'Distribution Center A', 'Distribution Center B', 'Distribution Center C', 'Distribution Center D',
             'Retail Store A', 'Retail Store B', 'Retail Store C', 'Retail Store D', 'Retail Store E',
             'Retail Store F', 'Retail Store G', 'Retail Store H', 'Retail Store I', 'Retail Store J']

for location in locations:
    G.add_node(location)

# Add edges (transportation routes) with random weights
edges = [('Factory A', 'Warehouse A'), ('Factory A', 'Warehouse B'), ('Factory B', 'Warehouse C'), ('Factory B', 'Warehouse D'),
         ('Warehouse A', 'Distribution Center A'), ('Warehouse A', 'Distribution Center B'), ('Warehouse B', 'Distribution Center A'), ('Warehouse B', 'Distribution Center B'),
         ('Warehouse C', 'Distribution Center C'), ('Warehouse C', 'Distribution Center D'), ('Warehouse D', 'Distribution Center C'), ('Warehouse D', 'Distribution Center D'),
         ('Distribution Center A', 'Retail Store A'), ('Distribution Center A', 'Retail Store B'), ('Distribution Center A', 'Retail Store C'), ('Distribution Center A', 'Retail Store D'),
         ('Distribution Center B', 'Retail Store C'), ('Distribution Center B', 'Retail Store D'), ('Distribution Center B', 'Retail Store E'), ('Distribution Center B', 'Retail Store F'),
         ('Distribution Center C', 'Retail Store E'), ('Distribution Center C', 'Retail Store F'), ('Distribution Center C', 'Retail Store G'), ('Distribution Center C', 'Retail Store H'),
         ('Distribution Center D', 'Retail Store G'), ('Distribution Center D', 'Retail Store H'), ('Distribution Center D', 'Retail Store I'), ('Distribution Center D', 'Retail Store J')]

for edge in edges:
    G.add_edge(edge[0], edge[1], weight=random.randint(10, 100))

# Visualize the graph with PyVis
net = Network(height='750px', width='100%', bgcolor='#F5F5F5', font_color='black')
net.barnes_hut(gravity=-80000, central_gravity=0.3, spring_length=100, spring_strength=0.001)

# Set node properties
node_color_map = {
    'Factory': 'red',
    'Warehouse': 'orange',
    'Distribution Center': 'green',
    'Retail Store': 'blue'
}

node_shape_map = {
    'Factory': 'square',
    'Warehouse': 'triangle',
    'Distribution Center': 'diamond',
    'Retail Store': 'circle'
}

node_size_map = {
    'Factory': 40,
    'Warehouse': 45,
    'Distribution Center': 30,
    'Retail Store': 25
}

default_color = 'gray'
default_shape = 'circle'
default_size = 25

for node in G.nodes:
    node_type = node.split()[0] if ' ' in node else 'Unknown'
    node_color = node_color_map.get(node_type, default_color)
    node_shape = node_shape_map.get(node_type, default_shape)
    node_size = node_size_map.get(node_type, default_size)
    net.add_node(node, label=node, color=node_color, shape=node_shape, size=node_size)

# Add edges
for edge in G.edges(data=True):
    source, target, attrs = edge
    weight = attrs['weight']
    net.add_edge(source, target, label=str(weight))

# Save the graph to an HTML file
graph_html_file = 'complex_supply_chain_graph.html'
net.save_graph(graph_html_file)
print(f"Graph exported to '{graph_html_file}'")

# Open the HTML file in a web browser
webbrowser.open_new_tab(graph_html_file)

import random

def get_latitude_for_node(node):
    return random.uniform(-90.0, 90.0)  # Generate random latitude between -90 and 90

def get_longitude_for_node(node):
    return random.uniform(-180.0, 180.0)  # Generate random longitude between -180 and 180


def networkx_to_neo4j(G, uri, user, password):
    try:
        # Create a Neo4j driver instance
        driver = GraphDatabase.driver(uri, auth=(user, password))

        # Create a session
        with driver.session() as session:
            # Clear the existing nodes and relationships in Neo4j
            session.run("MATCH (n) DETACH DELETE n")

            # Create nodes in Neo4j
            for node in G.nodes:
                node_type = node.split()[0]
                node_label = node_type.capitalize()

                # Get latitude and longitude (you'll need to implement this part)
                node_latitude = get_latitude_for_node(node)
                node_longitude = get_longitude_for_node(node)

                query = f"CREATE (n:{node_label} {{name: $name, latitude: $latitude, longitude: $longitude}})"
                session.run(query, name=node, latitude=node_latitude, longitude=node_longitude)

            # Create relationships in Neo4j
            for source, target, edge_data in G.edges(data=True):
                weight = edge_data['weight']
                query = "MATCH (a), (b) WHERE a.name = $source AND b.name = $target MERGE (a)-[r:TRANSPORTS {weight: $weight}]->(b)"
                session.run(query, source=source, target=target, weight=weight)

        print("Successfully imported graph into Neo4j!")
    except Exception as e:
        print(f"Error occurred while importing graph into Neo4j: {e}")
    finally:
        # Close the driver
        if driver:
            driver.close()


from neo4j import GraphDatabase

def run_astar_algo(uri, user, password, source_node, target_node):
    driver = GraphDatabase.driver(uri, auth=(user, password))

    query_project_graph = """
           CALL gds.graph.project(
               'supplyChainGraph',
               ['Factory', 'Warehouse', 'Distribution', 'Retail'],
               'TRANSPORTS',
                {
                    nodeProperties: ['latitude', 'longitude'],
                    relationshipProperties: 'weight'
                }
           )
       """

    query_astar_algo = f"""
            MATCH (source:Factory {{name: $source_node}}), (target:Retail {{name: $target_node}})
            CALL gds.shortestPath.astar.stream('supplyChainGraph', {{
                sourceNode: source,
                targetNode: target,
                latitudeProperty: 'latitude',
                longitudeProperty: 'longitude',
                relationshipWeightProperty: 'weight'
            }})
            YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
            RETURN
                index,
                gds.util.asNode(sourceNode).name AS sourceNodeName,
                gds.util.asNode(targetNode).name AS targetNodeName,
                totalCost,
                [nodeId IN nodeIds | gds.util.asNode(nodeId).name] AS nodeNames,
                costs,
                nodes(path) as path
            ORDER BY index
        """

    with driver.session() as session:
        # Delete any existing projected graph
        session.run("CALL gds.graph.drop('supplyChainGraph', false)")

        # Create the graph for A* algorithm
        session.run(query_project_graph)

        # Execute A* algorithm and find the shortest path
        result = session.run(query_astar_algo, source_node=source_node, target_node=target_node)

        # Print the shortest path and cost
        print(f"Shortest path from {source_node} to {target_node}:")
        for record in result:
            print(f"Path: {' -> '.join(record['nodeNames'])}, Total Cost: {record['totalCost']}")

    # Close the driver
    driver.close()

# Source and target nodes
source_node = "Factory A"
target_node = "Retail Store C"


def main():
    # Call the function to convert the NetworkX graph to Neo4j
    networkx_to_neo4j(G, uri, user, password)

    # Run the A* algorithm
    run_astar_algo(uri, user, password, source_node, target_node)

if __name__ == "__main__":
    main()

