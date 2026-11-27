# astra/tutor/schemas.py
"""
Pydantic schemas validating LLM-generated JSON before it's used to create DB rows.

Shapes mirror the prompts in tutor/prompts.py:
- StructureResponse: get_structure_generation_prompt (Ollama) - titles only, no content/quiz.
- CourseGenerationResponse: get_course_generation_prompt (Gemini fallback) - full structure + content + quiz.
- LessonContentResponse: get_lesson_content_prompt (Gemini per-lesson) - content + quiz for one lesson.

Fields that are purely cosmetic/optional (descriptions, objectives) default to "" if missing,
since a missing description shouldn't fail the whole generation. Fields that are structurally
required (titles, question text) are required, since their absence means the shape is genuinely
broken and the existing .get(..., 'Untitled ...') fallbacks in tasks.py would silently mask that.
"""
from typing import List, Optional
from pydantic import BaseModel


class QuizSchema(BaseModel):
    question: str
    options: List[str] = []
    answer: Optional[str] = None


class StructureLessonSchema(BaseModel):
    lesson_title: str


class StructureModuleSchema(BaseModel):
    module_title: str
    module_objective: str = ""
    lessons: List[StructureLessonSchema] = []


class StructureResponse(BaseModel):
    """Ollama structure-only output (get_structure_generation_prompt)."""
    course_title: str
    course_description: str = ""
    modules: List[StructureModuleSchema] = []


class ContentLessonSchema(BaseModel):
    lesson_title: str
    lesson_content: str = ""
    quiz: Optional[QuizSchema] = None


class ContentModuleSchema(BaseModel):
    module_title: str
    module_objective: str = ""
    lessons: List[ContentLessonSchema] = []


class CourseGenerationResponse(BaseModel):
    """Gemini full-course fallback output (get_course_generation_prompt)."""
    course_title: str
    course_description: str = ""
    modules: List[ContentModuleSchema] = []


class LessonContentResponse(BaseModel):
    """Gemini per-lesson content output (get_lesson_content_prompt)."""
    lesson_content: str = ""
    quiz: Optional[QuizSchema] = None
