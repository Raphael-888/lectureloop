
def next_prerequisite(concept_id, graph, mastery):
    """
    Find a prerequisite concept that needs further testing.
    """
    prerequisites = graph.get(concept_id, [])

    for concept in prerequisites:
        if concept not in mastery or mastery[concept] < 0.8:
            return concept

    return None
