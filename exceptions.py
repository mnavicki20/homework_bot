class EmptyListOrDictionaryError(Exception):
    """Пустой список или словарь."""

    pass


class ResponseStatusCodeError(Exception):
    """Некорректный статус ответа сервера."""

    pass


class RequestExceptionError(Exception):
    """Некорректный запрос."""

    pass


class IndefinеStatusError(Exception):
    """Неопределённый статус ответа."""

    pass
