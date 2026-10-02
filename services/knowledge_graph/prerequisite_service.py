from typing import Dict, List, Set, Tuple


class PrerequisiteService:
    """
    Manages prerequisite edges and learning dependency sequences between concepts.
    """

    DEFAULT_OS_PREREQUISITES: List[Tuple[str, str]] = [
        ("Process Basics", "Process State Transitions"),
        ("Process State Transitions", "CPU Scheduling"),
        ("CPU Scheduling", "Round Robin Scheduling"),
        ("Process Synchronization", "Semaphores"),
        ("Semaphores", "Critical Section Problem"),
        ("Critical Section Problem", "Deadlocks"),
        ("Deadlocks", "Banker's Algorithm"),
        ("Memory Basics", "Paging"),
        ("Paging", "Virtual Memory"),
        ("Virtual Memory", "Page Replacement (FIFO/LRU)"),
        ("File System Basics", "Disk Scheduling (SSTF/SCAN)")
    ]

    def __init__(self):
        self._prereqs: Dict[str, Set[str]] = {}
        for source, target in self.DEFAULT_OS_PREREQUISITES:
            self.add_prerequisite(source, target)

    def add_prerequisite(self, prerequisite_concept: str, target_concept: str):
        p_clean = prerequisite_concept.lower().strip()
        t_clean = target_concept.lower().strip()
        if t_clean not in self._prereqs:
            self._prereqs[t_clean] = set()
        self._prereqs[t_clean].add(p_clean)

    def get_prerequisites(self, concept_name: str) -> List[str]:
        c_clean = concept_name.lower().strip()
        return sorted(list(self._prereqs.get(c_clean, [])))

    def is_prerequisite(self, potential_prereq: str, target_concept: str) -> bool:
        p_clean = potential_prereq.lower().strip()
        t_clean = target_concept.lower().strip()
        return p_clean in self._prereqs.get(t_clean, set())
