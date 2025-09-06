from typing import List, Dict, Any

class Searcher:
    portal: str = "generic"
    def search(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        raise NotImplementedError
