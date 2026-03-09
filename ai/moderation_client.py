"""
Единый интерфейс для AI модерации контента через OpenAI API.
Использует GPT-4o mini для анализа изображений.
"""
import base64
import io
import logging
from enum import Enum
from typing import Optional, BinaryIO

from openai import AsyncOpenAI

from config import config

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Уровни риска контента."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModerationResult:
    """Результат проверки контента."""
    
    def __init__(
        self,
        risk_level: RiskLevel,
        confidence: float,
        details: Optional[str] = None,
        detected_issues: Optional[list[str]] = None
    ):
        self.risk_level = risk_level
        self.confidence = confidence
        self.details = details
        self.detected_issues = detected_issues or []
    
    def is_safe(self) -> bool:
        """Проверяет, является ли контент безопасным."""
        return self.risk_level == RiskLevel.LOW
    
    def requires_manual_review(self) -> bool:
        """Проверяет, требуется ли ручная модерация."""
        return self.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)


class ModerationClient:
    """
    Клиент для работы с OpenAI API для модерации контента.
    Использует GPT-4o mini для анализа изображений.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Инициализация клиента модерации.
        
        Args:
            api_key: API ключ OpenAI. Если None, берется из config.
            model: Модель OpenAI для использования.
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = model or config.AI_MODEL
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY не установлен. AI модерация будет недоступна.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info(f"ModerationClient инициализирован с моделью {self.model}")
    
    def is_available(self) -> bool:
        """Проверяет, доступен ли клиент OpenAI."""
        return self.client is not None
    
    async def check_image(
        self,
        image_data: bytes | BinaryIO,
        check_type: str = "general",
        prompt: Optional[str] = None
    ) -> ModerationResult:
        """
        Проверяет изображение на наличие запрещенного контента.
        
        Args:
            image_data: Данные изображения (bytes или BinaryIO).
            check_type: Тип проверки: "general", "nudity", "drugs", "violence".
            prompt: Дополнительный промпт для проверки.
        
        Returns:
            ModerationResult с результатом проверки.
        """
        if not self.is_available():
            logger.warning("OpenAI клиент недоступен. Возвращаем результат по умолчанию.")
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details="AI модерация недоступна - требуется ручная проверка"
            )
        
        try:
            # Преобразование изображения в base64
            if isinstance(image_data, bytes):
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            else:
                # BinaryIO
                image_data.seek(0)
                image_bytes = image_data.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Формирование промпта в зависимости от типа проверки
            system_prompt = self._get_system_prompt(check_type)
            user_prompt = prompt or self._get_user_prompt(check_type)
            
            # Вызов OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Парсинг ответа
            result = self._parse_response(response.choices[0].message.content, check_type)
            logger.info(f"Проверка изображения завершена. Уровень риска: {result.risk_level}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при проверке изображения через OpenAI: {e}", exc_info=True)
            # В случае ошибки возвращаем средний уровень риска для ручной проверки
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details=f"Ошибка при проверке: {str(e)}"
            )
    
    def _get_system_prompt(self, check_type: str) -> str:
        """Получает системный промпт в зависимости от типа проверки."""
        base_prompt = (
            "Ты - модератор контента для приложения знакомств. "
            "Твоя задача - анализировать изображения и определять уровень риска контента. "
            "Отвечай только в формате JSON с полями: risk_level (low/medium/high), confidence (0.0-1.0), "
            "details (краткое описание), detected_issues (массив найденных проблем)."
        )
        
        if check_type == "nudity":
            return base_prompt + (
                " Проверяй изображение на наличие обнаженного тела, интимных частей, "
                "сексуального контента. Низкий риск - обычные фото людей в одежде. "
                "Высокий риск - обнаженное тело, интимные части, сексуальные позы."
            )
        elif check_type == "drugs":
            return base_prompt + (
                " Проверяй изображение на наличие наркотических веществ, "
                "наркотиков, сигарет, алкоголя в неуместном контексте. "
                "Низкий риск - обычные фото без запрещенных веществ. "
                "Высокий риск - явные наркотики, употребление наркотиков."
            )
        elif check_type == "violence":
            return base_prompt + (
                " Проверяй изображение на наличие насилия, оружия, агрессии. "
                "Низкий риск - обычные фото без насилия. "
                "Высокий риск - оружие, насилие, агрессивные действия."
            )
        else:
            return base_prompt + (
                " Проверяй изображение на все виды запрещенного контента: "
                "обнаженное тело, наркотики, насилие, оружие, запрещенные символы. "
                "Низкий риск - безопасный контент. "
                "Высокий риск - явно запрещенный контент."
            )
    
    def _get_user_prompt(self, check_type: str) -> str:
        """Получает пользовательский промпт в зависимости от типа проверки."""
        if check_type == "nudity":
            return "Проанализируй это изображение на наличие обнаженного тела или сексуального контента."
        elif check_type == "drugs":
            return "Проанализируй это изображение на наличие наркотических веществ или наркотиков."
        elif check_type == "violence":
            return "Проанализируй это изображение на наличие насилия, оружия или агрессии."
        else:
            return "Проанализируй это изображение на наличие любого запрещенного контента."
    
    def _parse_response(self, response_text: str, check_type: str) -> ModerationResult:
        """
        Парсит ответ от OpenAI и создает ModerationResult.
        
        Args:
            response_text: Текст ответа от OpenAI.
            check_type: Тип проверки.
        
        Returns:
            ModerationResult с результатом проверки.
        """
        import json
        import re
        
        try:
            # Попытка извлечь JSON из ответа
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Если JSON не найден, пытаемся парсить текст
                data = self._parse_text_response(response_text)
            
            risk_level_str = data.get("risk_level", "medium").lower()
            if risk_level_str == "low":
                risk_level = RiskLevel.LOW
            elif risk_level_str == "high":
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.MEDIUM
            
            confidence = float(data.get("confidence", 0.5))
            details = data.get("details", "")
            detected_issues = data.get("detected_issues", [])
            
            if not isinstance(detected_issues, list):
                detected_issues = []
            
            return ModerationResult(
                risk_level=risk_level,
                confidence=confidence,
                details=details,
                detected_issues=detected_issues
            )
            
        except Exception as e:
            logger.warning(f"Ошибка при парсинге ответа OpenAI: {e}. Ответ: {response_text}")
            # Если не удалось распарсить, анализируем текст ответа
            return self._parse_text_response(response_text)
    
    def _parse_text_response(self, response_text: str) -> dict:
        """
        Парсит текстовый ответ, если JSON не найден.
        
        Args:
            response_text: Текст ответа.
        
        Returns:
            Словарь с данными результата.
        """
        response_lower = response_text.lower()
        
        # Определение уровня риска по ключевым словам
        if any(word in response_lower for word in ["high", "высокий", "опасно", "запрещено", "явно"]):
            risk_level = "high"
            confidence = 0.8
        elif any(word in response_lower for word in ["low", "низкий", "безопасно", "нормально", "ok"]):
            risk_level = "low"
            confidence = 0.7
        else:
            risk_level = "medium"
            confidence = 0.5
        
            return {
                "risk_level": risk_level,
                "confidence": confidence,
                "details": response_text[:200],  # Первые 200 символов
                "detected_issues": []
            }
    
    async def check_text(
        self,
        text: str,
        check_type: str = "general"
    ) -> ModerationResult:
        """
        Проверяет текст на наличие запрещенного контента через OpenAI Moderation API и GPT.
        Использует комбинированный подход для более точного определения наркотиков и алкоголя.
        
        Args:
            text: Текст для проверки
            check_type: Тип проверки: "general", "nudity", "drugs", "violence"
        
        Returns:
            ModerationResult с результатом проверки
        """
        if not self.is_available():
            logger.warning("OpenAI клиент недоступен. Возвращаем результат по умолчанию.")
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details="AI модерация недоступна - требуется ручная проверка"
            )
        
        try:
            # Сначала проверяем через Moderation API
            moderation_result = await self.client.moderations.create(
                input=text
            )
            
            mod_result = moderation_result.results[0]
            
            # Дополнительная проверка через GPT для наркотиков и алкоголя
            # (Moderation API может пропускать эти категории)
            gpt_result = await self._check_text_with_gpt(text)
            
            # Объединяем результаты
            if mod_result.flagged or gpt_result:
                # Если Moderation API нашел нарушения
                if mod_result.flagged:
                    high_risk_categories = [
                        mod_result.categories.sexual,
                        mod_result.categories.hate,
                        mod_result.categories.violence,
                        mod_result.categories.self_harm,
                        mod_result.categories.sexual_minors,
                        mod_result.categories.hate_threatening,
                        mod_result.categories.violence_graphic
                    ]
                    
                    if any(high_risk_categories):
                        risk_level = RiskLevel.HIGH
                        confidence = max([
                            mod_result.category_scores.sexual,
                            mod_result.category_scores.hate,
                            mod_result.category_scores.violence,
                            mod_result.category_scores.self_harm,
                            mod_result.category_scores.sexual_minors,
                            mod_result.category_scores.hate_threatening,
                            mod_result.category_scores.violence_graphic
                        ])
                    else:
                        risk_level = RiskLevel.MEDIUM
                        confidence = max([
                            mod_result.category_scores.harassment,
                            mod_result.category_scores.harassment_threatening,
                            mod_result.category_scores.self_harm_intent,
                            mod_result.category_scores.self_harm_instructions
                        ])
                    
                    detected_issues = []
                    if mod_result.categories.sexual or mod_result.categories.sexual_minors:
                        detected_issues.append("nudity")
                    if mod_result.categories.violence or mod_result.categories.violence_graphic:
                        detected_issues.append("violence")
                    if mod_result.categories.hate or mod_result.categories.hate_threatening:
                        detected_issues.append("hate")
                    if mod_result.categories.self_harm or mod_result.categories.self_harm_intent or mod_result.categories.self_harm_instructions:
                        detected_issues.append("self_harm")
                    if mod_result.categories.harassment or mod_result.categories.harassment_threatening:
                        detected_issues.append("harassment")
                    
                    details = f"Обнаружены нарушения: {', '.join(detected_issues) if detected_issues else 'запрещенный контент'}"
                    
                    # Если GPT тоже нашел нарушения, повышаем уровень риска
                    if gpt_result:
                        if gpt_result.risk_level == RiskLevel.HIGH:
                            risk_level = RiskLevel.HIGH
                            confidence = max(confidence, gpt_result.confidence)
                        elif gpt_result.risk_level == RiskLevel.MEDIUM and risk_level == RiskLevel.LOW:
                            risk_level = RiskLevel.MEDIUM
                            confidence = max(confidence, gpt_result.confidence)
                        
                        if gpt_result.detected_issues:
                            detected_issues.extend(gpt_result.detected_issues)
                            detected_issues = list(set(detected_issues))  # Удаляем дубликаты
                        
                        if gpt_result.details:
                            details += f". {gpt_result.details}"
                    
                    return ModerationResult(
                        risk_level=risk_level,
                        confidence=float(confidence),
                        details=details,
                        detected_issues=detected_issues
                    )
                else:
                    # Moderation API не нашел, но GPT нашел - используем результат GPT
                    return gpt_result
            else:
                # Оба метода не нашли нарушений
                return ModerationResult(
                    risk_level=RiskLevel.LOW,
                    confidence=1.0 - max([
                        mod_result.category_scores.sexual,
                        mod_result.category_scores.hate,
                        mod_result.category_scores.violence,
                        mod_result.category_scores.self_harm
                    ]),
                    details="Текст безопасен",
                    detected_issues=[]
                )
            
        except Exception as e:
            logger.error(f"Ошибка при проверке текста через OpenAI: {e}", exc_info=True)
            # В случае ошибки возвращаем средний уровень риска для ручной проверки
            return ModerationResult(
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                details=f"Ошибка при проверке: {str(e)}"
            )
    
    async def _check_text_with_gpt(self, text: str) -> Optional[ModerationResult]:
        """
        Дополнительная проверка текста через GPT с фокусом на наркотики и алкоголь.
        
        Args:
            text: Текст для проверки
        
        Returns:
            ModerationResult если найдены нарушения, None если все в порядке
        """
        try:
            system_prompt = (
                "Ты - модератор контента для приложения знакомств. "
                "Твоя задача - анализировать тексты и определять уровень риска контента. "
                "Особое внимание уделяй упоминаниям наркотиков, алкоголя, запрещенных веществ. "
                "Отвечай только в формате JSON с полями: risk_level (low/medium/high), confidence (0.0-1.0), "
                "details (краткое описание), detected_issues (массив найденных проблем)."
            )
            
            user_prompt = (
                f"Проанализируй этот текст из профиля знакомств на наличие запрещенного контента:\n\n"
                f"{text}\n\n"
                f"Проверь на:\n"
                f"- Упоминания наркотиков, наркотических веществ, психоактивных веществ\n"
                f"- Упоминания алкоголя в контексте употребления или продажи\n"
                f"- Сексуальный контент, обнаженное тело\n"
                f"- Насилие, оружие, агрессию\n"
                f"- Ненависть, дискриминацию\n"
                f"- Призывы к самоубийству или самоповреждению\n\n"
                f"Определи уровень риска:\n"
                f"- low - безопасный текст без нарушений\n"
                f"- medium - сомнительный контент, требующий проверки\n"
                f"- high - явно запрещенный контент (наркотики, алкоголь, сексуальный контент, насилие)"
            )
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Парсим ответ
            response_text = response.choices[0].message.content
            result = self._parse_response(response_text, "general")
            
            # Если нашли нарушения, возвращаем результат
            if result.requires_manual_review():
                logger.info(f"GPT обнаружил нарушения в тексте: {result.risk_level}, confidence: {result.confidence:.2f}")
                return result
            
            return None
            
        except Exception as e:
            logger.warning(f"Ошибка при проверке текста через GPT: {e}")
            return None


# Глобальный экземпляр клиента
_moderation_client: Optional[ModerationClient] = None


def get_moderation_client() -> ModerationClient:
    """
    Получает глобальный экземпляр клиента модерации.
    
    Returns:
        ModerationClient: Экземпляр клиента модерации.
    """
    global _moderation_client
    
    if _moderation_client is None:
        _moderation_client = ModerationClient()
    
    return _moderation_client
