#!/usr/bin/env python3
"""
Модератор контента для проверки промптов на соответствие политике Imagen
"""
import os
import re
from typing import Dict, List, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class ContentModerationResult:
    def __init__(self, is_safe: bool, reasons: List[str] = None, suggested_fix: str = None):
        self.is_safe = is_safe
        self.reasons = reasons or []
        self.suggested_fix = suggested_fix

class ContentModerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Список запрещенных тем для Imagen
        self.forbidden_keywords = [
            # Насилие и вред
            "violence", "blood", "gore", "murder", "killing", "death", "torture", "weapon",
            "gun", "knife", "sword", "bomb", "explosion", "war", "fight", "attack",
            "injury", "wound", "hurt", "damage", "harm", "pain", "suffering",
            "насилие", "кровь", "убийство", "смерть", "пытки", "оружие", "пистолет", 
            "нож", "меч", "бомба", "взрыв", "война", "драка", "атака", "ранение",
            "рана", "травма", "повреждение", "вред", "боль", "страдание", "упала",
            "упал", "сломал", "сломала", "отрезал", "отрезала", "отрубил", "отрубила",
            
            # Взрослый контент
            "nude", "naked", "sex", "porn", "erotic", "sexy", "breast", "nipple",
            "голый", "секс", "порно", "эротика", "сексуальный", "грудь",
            
            # Наркотики и алкоголь
            "drug", "cocaine", "heroin", "marijuana", "alcohol", "drunk", "smoking",
            "наркотики", "кокаин", "героин", "марихуана", "алкоголь", "пьяный", "курение",
            
            # Дискриминация
            "racist", "discrimination", "hate", "nazi", "supremacist",
            "расист", "дискриминация", "ненависть", "нацист",
            
            # Политика
            "politician", "election", "voting", "political", "protest",
            "политик", "выборы", "голосование", "политический", "протест"
        ]

    def moderate_prompt(self, prompt: str) -> ContentModerationResult:
        """
        Проверяет промпт на соответствие политике контента Imagen
        """
        if not prompt or len(prompt.strip()) < 3:
            return ContentModerationResult(
                is_safe=False,
                reasons=["Промпт слишком короткий"],
                suggested_fix="Опишите более детально, что вы хотите создать"
            )
        
        # Быстрая проверка по ключевым словам
        prompt_lower = prompt.lower()
        found_keywords = [word for word in self.forbidden_keywords if word in prompt_lower]
        
        # Дополнительная проверка на контекстные фразы с травмами
        injury_patterns = [
            "упала голов", "упал голов", "отрезанн", "сломанн", 
            "без голов", "без рук", "без ног", "потерял голов",
            "оторванн", "отрубленн", "ампутир", "изувеченн"
        ]
        
        found_injury_patterns = [pattern for pattern in injury_patterns if pattern in prompt_lower]
        
        if found_keywords or found_injury_patterns:
            all_violations = found_keywords + found_injury_patterns
            return ContentModerationResult(
                is_safe=False,
                reasons=[f"Обнаружены запрещенные темы: {', '.join(all_violations)}"],
                suggested_fix="Попробуйте описать персонажа без упоминания травм, повреждений или запрещенных тем"
            )
        
        # Глубокая проверка с помощью Gemini
        return self._check_with_gemini(prompt)
    
    def _check_with_gemini(self, prompt: str) -> ContentModerationResult:
        """
        Использует Gemini для анализа промпта
        """
        try:
            analysis_prompt = f"""
Проанализируй следующий промпт для генерации изображения и определи, нарушает ли он политику контента Google Imagen.

Политика запрещает:
1. Насилие, кровь, оружие, смерть, травмы, повреждения
2. Взрослый/сексуальный контент
3. Наркотики и алкоголь
4. Дискриминацию и ненависть
5. Известных людей (политиков, актеров)
6. Контент, который может причинить вред

ОСОБОЕ ВНИМАНИЕ к описаниям травм и повреждений:
- "упала голова", "отрезанная рука", "сломанная нога"
- "ранение", "кровотечение", "боль"
- любые описания физического вреда или увечий

Промпт: "{prompt}"

Ответь в формате JSON:
{{
  "is_safe": true/false,
  "reasons": ["список причин если небезопасно"],
  "suggested_fix": "предложение как исправить промпт"
}}
"""
            
            response = self.model.generate_content(analysis_prompt)
            
            # Извлекаем JSON из ответа
            response_text = response.text.strip()
            
            # Простой парсинг JSON (можно улучшить)
            if "\"is_safe\": false" in response_text or "\"is_safe\":false" in response_text:
                reasons = self._extract_reasons(response_text)
                suggested_fix = self._extract_suggestion(response_text)
                return ContentModerationResult(
                    is_safe=False,
                    reasons=reasons,
                    suggested_fix=suggested_fix
                )
            else:
                return ContentModerationResult(is_safe=True)
                
        except Exception as e:
            print(f"Error in Gemini moderation: {e}")
            # В случае ошибки разрешаем промпт
            return ContentModerationResult(is_safe=True)
    
    def _extract_reasons(self, text: str) -> List[str]:
        """Извлекает причины из JSON ответа"""
        try:
            # Ищем массив reasons
            import json
            # Простой поиск JSON в тексте
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                return data.get('reasons', ['Неподходящий контент'])
        except:
            pass
        return ['Неподходящий контент']
    
    def _extract_suggestion(self, text: str) -> str:
        """Извлекает предложение по исправлению"""
        try:
            import json
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                return data.get('suggested_fix', 'Попробуйте изменить описание')
        except:
            pass
        return 'Попробуйте изменить описание'

# Глобальный экземпляр модератора
moderator = ContentModerator()

def check_prompt_safety(prompt: str) -> ContentModerationResult:
    """
    Удобная функция для проверки промпта
    """
    return moderator.moderate_prompt(prompt) 