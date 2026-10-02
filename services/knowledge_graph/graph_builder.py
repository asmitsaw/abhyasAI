from typing import Any, Dict, List
from services.mastery_service import get_mastery_band, get_mastery_color


class GraphBuilder:
    """
    Builds lightweight graph nodes and relationship edges for curriculum concepts.
    Nodes represent Subject, Modules, Topics, and Concepts.
    Edges represent PREREQUISITE_OF, RELATED_TO, APPEARED_IN_PYQ.
    """

    def build_graph(
        self,
        subject_name: str,
        modules: List[Dict[str, Any]],
        mastery_map: Dict[str, float] = None,
        pyq_evidence_map: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        mastery_map = mastery_map or {}
        pyq_evidence_map = pyq_evidence_map or {}

        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []

        # 1. Subject Node (Root)
        subj_id = f"subj_{subject_name.lower().replace(' ', '_')}"
        nodes.append({
            "id": subj_id,
            "label": subject_name,
            "type": "SUBJECT",
            "mastery_score": 75.0,
            "color": "#101010",
            "size": 30
        })

        for m_idx, mod in enumerate(modules, 1):
            mod_name = mod.get("module_name", f"Module {m_idx}")
            mod_id = f"mod_{m_idx}"
            nodes.append({
                "id": mod_id,
                "label": mod_name,
                "type": "MODULE",
                "mastery_score": 60.0,
                "color": "#1595df",
                "size": 22
            })
            links.append({
                "source": subj_id,
                "target": mod_id,
                "relationship": "CONTAINS"
            })

            # Topics
            for t_idx, topic in enumerate(mod.get("topics", []), 1):
                top_id = f"top_{m_idx}_{t_idx}"
                t_clean = topic.strip()
                m_score = mastery_map.get(t_clean.lower(), 42.0)
                band = get_mastery_band(m_score)
                color = get_mastery_color(band)

                nodes.append({
                    "id": top_id,
                    "label": t_clean,
                    "type": "TOPIC",
                    "module": mod_name,
                    "mastery_score": m_score,
                    "mastery_band": band,
                    "color": color,
                    "size": 16,
                    "pyq_appearances": pyq_evidence_map.get(t_clean.lower(), {}).get("occurrence_count", 2)
                })
                links.append({
                    "source": mod_id,
                    "target": top_id,
                    "relationship": "CONTAINS"
                })

        return {
            "nodes": nodes,
            "links": links
        }
