from typing import Any, Dict, List, Optional
from services.knowledge_graph.graph_builder import GraphBuilder
from services.knowledge_graph.prerequisite_service import PrerequisiteService
from services.mastery_service import MasteryService


class KnowledgeGraphService:
    """
    Knowledge graph service providing interactive curriculum nodes and dependency networks.
    """

    def __init__(
        self,
        mastery_service: Optional[MasteryService] = None
    ):
        self.mastery_service = mastery_service or MasteryService()
        self.builder = GraphBuilder()
        self.prereqs = PrerequisiteService()

    def get_subject_graph(
        self,
        student_id: int,
        subject_name: str = "Operating Systems"
    ) -> Dict[str, Any]:
        # Fetch actual student mastery
        mastery_res = self.mastery_service.get_subject_mastery(student_id, subject_name)
        mastery_map = {t["topic_name"].lower(): t["mastery_score"] for t in mastery_res.get("topics", [])}

        # Default Operating Systems curriculum modules
        default_modules = [
            {
                "module_name": "Module 1: Process Management",
                "topics": ["Process State Transitions", "CPU Scheduling (FCFS/RR)", "Inter-process Communication", "Deadlocks & Banker's Algorithm"]
            },
            {
                "module_name": "Module 2: Memory Management",
                "topics": ["Paging & Segmentation", "Virtual Memory", "Page Replacement (FIFO/LRU)", "Thrashing"]
            },
            {
                "module_name": "Module 3: Storage & File Systems",
                "topics": ["Disk Scheduling (SSTF/SCAN)", "File Allocation Methods", "Directory Structures"]
            }
        ]

        graph = self.builder.build_graph(
            subject_name=subject_name,
            modules=default_modules,
            mastery_map=mastery_map
        )

        return {
            "subject": subject_name,
            "overall_mastery": mastery_res.get("overall_mastery", 45.0),
            "graph": graph
        }


_global_kg_service: Optional[KnowledgeGraphService] = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    global _global_kg_service
    if _global_kg_service is None:
        _global_kg_service = KnowledgeGraphService()
    return _global_kg_service
