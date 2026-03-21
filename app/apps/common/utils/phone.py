"""Утилиты для работы с телефонными номерами."""
import re


def normalize_phone(phone: str) -> str:
    """
    Нормализует телефонный номер к формату +996XXXXXXXXX.
    
    Принимает форматы:
    - 0558000350
    - +996558000350
    - 996558000350
    - 558000350
    
    Возвращает:
    - +996558000350
    
    Args:
        phone: Телефонный номер в любом формате
        
    Returns:
        Нормализованный телефонный номер с префиксом +996
        
    Raises:
        ValueError: Если номер не может быть нормализован
    """
    if not phone:
        raise ValueError("Телефон не может быть пустым")
    
    # Удаляем все нецифровые символы, кроме +
    phone = re.sub(r'[^\d+]', '', phone.strip())
    
    # Если номер уже начинается с +996
    if phone.startswith('+996'):
        digits = phone[1:]  # Убираем + для проверки
        if len(digits) == 12:
            return phone
        raise ValueError(f"Неверный формат номера: {phone}")
    
    # Если номер начинается с 996
    if phone.startswith('996'):
        if len(phone) == 12:
            return '+' + phone
        raise ValueError(f"Неверный формат номера: {phone}")
    
    # Если номер начинается с 0 (кыргызский формат)
    if phone.startswith('0'):
        if len(phone) == 10:
            return '+996' + phone[1:]
        raise ValueError(f"Неверный формат номера: {phone}")
    
    # Если номер без префикса (9 цифр без 0)
    if len(phone) == 9:
        return '+996' + phone
    
    # Если номер без префикса (10 цифр с ведущим 0)
    if len(phone) == 10 and phone.startswith('0'):
        return '+996' + phone[1:]
    
    raise ValueError(f"Невозможно нормализовать номер: {phone}. Ожидается формат: 0558000350, +996558000350, 996558000350")


def is_valid_phone(phone: str) -> bool:
    """
    Проверяет, является ли номер телефона валидным.
    
    Args:
        phone: Телефонный номер
        
    Returns:
        True если номер валидный, False в противном случае
    """
    try:
        normalized = normalize_phone(phone)
        # Проверяем, что после +996 идет 9 цифр
        digits_only = normalized[1:]  # Убираем +
        return len(digits_only) == 12 and digits_only.startswith('996')
    except ValueError:
        return False
