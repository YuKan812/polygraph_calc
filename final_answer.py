from typing import Any
from smolagents.tools import Tool

class FinalAnswerTool(Tool):
    name = "final_answer"
    description = "Предоставляет окончательный ответ пользователю. Используй этот инструмент ОБЯЗАТЕЛЬНО в конце работы."
    inputs = {
        'answer': {
            'type': 'string', 
            'description': 'Финальный ответ для пользователя. Должен быть четким, структурированным и содержать все важные данные из расчета.'
        }
    }
    output_type = "string"

    def forward(self, answer: str) -> str:
        """Возвращает финальный ответ"""
        return f"\n{'='*60}\n✅ РЕЗУЛЬТАТ:\n{'='*60}\n{answer}\n{'='*60}\n"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_initialized = True