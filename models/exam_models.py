from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class SyllabusModule(BaseModel):
    module_name: str = Field(description="Name or title of the module, e.g. 'Module 1: Process Management'")
    topics: List[str] = Field(description="List of key topics covered in this module")


class Syllabus(BaseModel):
    subject_name: Optional[str] = Field(default="Subject", description="Name of the subject if detected")
    modules: List[SyllabusModule] = Field(description="List of modules in the syllabus")


class PYQQuestionAnalysis(BaseModel):
    question: str = Field(description="Extracted question text from previous year paper")
    marks: int = Field(description="Marks allocated to this question")
    module: str = Field(description="Associated syllabus module name")
    topic: str = Field(description="Specific topic within the module")
    question_type: str = Field(description="Question type, e.g. Short Answer, Numerical, Descriptive, Diagram-based")
    difficulty: str = Field(description="Difficulty level: Easy, Medium, or Hard")


class PYQAnalysis(BaseModel):
    question_analyses: List[PYQQuestionAnalysis] = Field(description="Detailed analysis of questions extracted from past papers")
    module_weightage: Dict[str, float] = Field(description="Estimated module weightage percentage based on past papers")
    frequently_asked_topics: List[str] = Field(description="List of recurring or frequently asked topics across past papers")
    common_question_patterns: List[str] = Field(description="Observed question formatting or structural patterns")
    pyq_paper_structure_pattern: Optional[str] = Field(default="", description="Summary of the structural pattern identified in past papers (e.g., Section A 2-marks compulsory, Section B 6-7 marks module internal choices OR options)")


class BlueprintQuestionSpec(BaseModel):
    question_number: str = Field(description="Question identifier, e.g. 'Q1(a)', 'Q2'")
    target_module: str = Field(description="Assigned syllabus module for this question")
    target_topic: str = Field(description="Assigned topic for this question")
    marks: int = Field(description="Allocated marks for this question")
    question_type: str = Field(description="Target question type (e.g., Short Explanation, Long Problem, Numerical)")
    difficulty: str = Field(description="Target difficulty: Easy, Medium, or Hard")
    or_choice_group: Optional[str] = Field(default="", description="Identifier for internal choices, e.g., 'Q1_OR', 'Q2_OR'")


class ExamBlueprint(BaseModel):
    paper_type: str = Field(description="Paper type, e.g. Unit Test, End Semester Exam, Mid Sem")
    total_marks: int = Field(description="Total marks for the paper")
    selected_modules: List[str] = Field(description="List of modules included in this paper")
    format_pattern: Optional[str] = Field(default="Standard Module Choice (6-7 marks + 2 marks short)", description="Exam paper structural pattern description")
    question_specs: List[BlueprintQuestionSpec] = Field(description="Planned specifications for each question in the paper")


class ExamQuestion(BaseModel):
    question_number: str = Field(description="Question identifier, e.g. 'Q1(a)'")
    question_text: str = Field(description="The full text of the exam question")
    marks: int = Field(description="Marks for this question")
    module: str = Field(description="Module name from syllabus")
    topic: str = Field(description="Topic name from syllabus")
    question_type: str = Field(description="Type of question")
    difficulty: str = Field(description="Difficulty level: Easy, Medium, or Hard")
    or_choice_group: Optional[str] = Field(default="", description="If part of an internal OR choice group (e.g. 'Q1_OR')")
    is_optional_choice: Optional[bool] = Field(default=False, description="True if this is the alternative OR option")
    solution_hint: Optional[str] = Field(default="", description="Brief hint or key points for answering")


class ExamSection(BaseModel):
    section_title: str = Field(description="Section heading, e.g. 'Section A (Attempt All Questions)'")
    instructions: str = Field(description="Specific instructions for this section, e.g. 'Answer any 2 questions'")
    section_marks: int = Field(description="Total marks for this section")
    questions: List[ExamQuestion] = Field(description="List of questions in this section")


class PracticePaper(BaseModel):
    title: str = Field(description="Paper title, e.g. 'Operating Systems - Unit Test 1'")
    total_marks: int = Field(description="Total marks of the paper")
    duration_minutes: Optional[int] = Field(default=60, description="Recommended time duration in minutes")
    general_instructions: List[str] = Field(description="List of general exam instructions for students")
    sections: List[ExamSection] = Field(description="Sections comprising the exam paper")


class PracticePaperSet(BaseModel):
    paper_1: PracticePaper = Field(description="Practice Paper 1 (Set A)")
    paper_2: PracticePaper = Field(description="Practice Paper 2 (Set B)")
