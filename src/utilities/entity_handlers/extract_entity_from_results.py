def extract_entities_from_results(results):

    entities = set()

    for item in results[:2]:
        entities.update([i.strip() for i in item["entities"].split(',')])

    return list(entities)