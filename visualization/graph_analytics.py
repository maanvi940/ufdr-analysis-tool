import networkx as nx
import sqlite3
import pandas as pd
from collections import defaultdict
import math

class ForensicGraphAnalyzer:
    """
    Analyzes communication networks from forensic data using NetworkX.
    """
    def __init__(self, db_path='forensic_data.db'):
        self.db_path = db_path

    def build_communication_graph(self, case_id, min_interactions=1):
        """
        Builds a directed graph of communications (calls + messages).
        Nodes: Phone numbers (normalized)
        Edges: Weighted by number of interactions
        """
        G = nx.DiGraph()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 1. Calls
            cursor = conn.execute("""
                SELECT caller_digits, receiver_digits 
                FROM calls 
                WHERE case_id = ?
            """, (case_id,))
            
            for caller, receiver in cursor.fetchall():
                if caller and receiver:
                    if G.has_edge(caller, receiver):
                        G[caller][receiver]['weight'] += 1
                        G[caller][receiver]['calls'] += 1
                    else:
                        G.add_edge(caller, receiver, weight=1, calls=1, messages=0)
            
            # 2. Messages
            cursor = conn.execute("""
                SELECT sender_digits, receiver_digits 
                FROM messages 
                WHERE case_id = ?
            """, (case_id,))
            
            for sender, receiver in cursor.fetchall():
                if sender and receiver:
                    if G.has_edge(sender, receiver):
                        G[sender][receiver]['weight'] += 1
                        G[sender][receiver]['messages'] += 1
                    else:
                        G.add_edge(sender, receiver, weight=1, calls=0, messages=1)
            
            # Enrich nodes with contact names
            try:
                # Get all unique numbers in the graph
                node_list = list(G.nodes())
                if node_list:
                    # Fetch contact names
                    placeholders = ','.join(['?'] * len(node_list))
                    query = f"SELECT phone_digits, name FROM contacts WHERE case_id = ? AND phone_digits IN ({placeholders})"
                    params = [case_id] + node_list
                    
                    cursor = conn.execute(query, params)
                    contact_map = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    # Update graph nodes
                    for node in G.nodes():
                        name = contact_map.get(node, "Unknown")
                        nx.set_node_attributes(G, {node: {'name': name, 'phone': node}})
            except Exception as e:
                print(f"Error enriching graph identifiers: {e}")

            conn.close()
            
            # Filter by min interactions
            if min_interactions > 1:
                edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < min_interactions]
                G.remove_edges_from(edges_to_remove)
                # Remove isolated nodes caused by edge removal
                G.remove_nodes_from(list(nx.isolates(G)))
                
        except Exception as e:
            print(f"Error building graph: {e}")
            
        return G

    def calculate_centrality_metrics(self, G, top_n=10):
        """
        Calculates key centrality metrics for the graph.
        Returns a dictionary of metrics, each being a list of (node, score) tuples.
        """
        if G.number_of_nodes() == 0:
            return {}
            
        metrics = {}
        
        # 1. Degree Centrality (Total connections)
        try:
            dc = nx.degree_centrality(G)
            metrics['degree_centrality'] = sorted(dc.items(), key=lambda x: x[1], reverse=True)[:top_n]
        except:
            metrics['degree_centrality'] = []

        # 2. Betweenness Centrality (Bridge nodes)
        try:
            bc = nx.betweenness_centrality(G, weight=None) # Unweighted for topological betweenness
            metrics['betweenness_centrality'] = sorted(bc.items(), key=lambda x: x[1], reverse=True)[:top_n]
        except:
            metrics['betweenness_centrality'] = []

        # 3. Closeness Centrality (Speed of reach)
        try:
            cc = nx.closeness_centrality(G)
            metrics['closeness_centrality'] = sorted(cc.items(), key=lambda x: x[1], reverse=True)[:top_n]
        except:
            metrics['closeness_centrality'] = []

        # 4. PageRank (Influence)
        try:
            pr = nx.pagerank(G, weight='weight')
            metrics['pagerank'] = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:top_n]
        except:
            metrics['pagerank'] = []
            
        # 5. Eigenvector Centrality (Connected to connected nodes)
        try:
            # Use max_iter to prevent convergence errors on large sparse graphs
            ec = nx.eigenvector_centrality(G, max_iter=1000, weight='weight')
            metrics['eigenvector_centrality'] = sorted(ec.items(), key=lambda x: x[1], reverse=True)[:top_n]
        except:
            metrics['eigenvector_centrality'] = []
            
        return metrics

    def detect_communities(self, G):
        """
        Detect communities using greedy modularity optimization.
        """
        from networkx.algorithms import community
        
        if G.number_of_nodes() == 0:
            return {'communities': [], 'modularity': 0}
            
        # Convert to undirected for community detection
        G_undirected = G.to_undirected()
        
        try:
            communities = list(community.greedy_modularity_communities(G_undirected))
            # Convert frozensets to lists
            communities_list = [list(c) for c in communities]
            
            # Map node to community ID
            node_community = {}
            for i, comm in enumerate(communities_list):
                for node in comm:
                    node_community[node] = i
            
            return {
                'communities': communities_list,
                'node_community': node_community,
                'num_communities': len(communities_list)
            }
        except Exception as e:
            print(f"Community detection error: {e}")
            return {'communities': [], 'node_community': {}, 'num_communities': 0}

    def get_ego_network(self, G, root, radius=1):
        """
        Returns the ego network for a given node.
        """
        try:
            if root not in G:
                return nx.DiGraph()
            return nx.ego_graph(G, root, radius=radius)
        except Exception as e:
            print(f"Ego network error: {e}")
            return nx.DiGraph()

    def identify_bridges(self, G, top_n=10):
        """
        Identify bridge nodes based on betweenness centrality relative to degree.
        Returns list of (node, score, betweenness, degree).
        """
        if G.number_of_nodes() == 0:
            return []
            
        bridges = []
        try:
            bc = nx.betweenness_centrality(G)
            deg = dict(G.degree())
            
            for node, betweenness in bc.items():
                degree = deg.get(node, 0)
                if degree > 0:
                    # Score favoring high betweenness but penalizing very high degree (hubs)
                    # Heuristic: betweenness / log(degree + 2)
                    score = betweenness / (math.log(degree + 2))
                    bridges.append((node, score, betweenness, degree))
            
            bridges.sort(key=lambda x: x[1], reverse=True)
            return bridges[:top_n]
        except Exception as e:
            print(f"Bridge identification error: {e}")
            return []

    def find_cliques(self, G, min_size=3):
        """
        Find cliques in the graph.
        """
        if G.number_of_nodes() == 0:
            return []
            
        try:
            G_undirected = G.to_undirected()
            cliques = list(nx.find_cliques(G_undirected))
            return [c for c in cliques if len(c) >= min_size]
        except Exception as e:
            print(f"Clique detection error: {e}")
            return []
