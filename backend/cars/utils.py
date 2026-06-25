from rest_framework import status
from rest_framework.response import Response
from .models import Statuses

# ==================================================================== #
#  Хелперы                                                             #
# ==================================================================== #


def problem_response(
    problem_type: str,
    title: str,
    detail: str,
    instance: str,
    http_status: int,
) -> Response:
    """Формирует ответ в формате application/problem+json (RFC 7807)."""
    return Response(
        {
            "type": problem_type,
            "title": title,
            "status": http_status,
            "detail": detail,
            "instance": instance,
        },
        status=http_status,
        content_type="application/problem+json",
    )


def conflict_response(problem_type, title, detail, instance) -> Response:
    return problem_response(
        problem_type, title, detail, instance, status.HTTP_409_CONFLICT
    )


def forbidden_response(detail, instance) -> Response:
    return problem_response(
        problem_type="/problems/forbidden",
        title="Доступ запрещён",
        detail=detail,
        instance=instance,
        http_status=status.HTTP_403_FORBIDDEN,
    )


# ==================================================================== #
#  Конфигурация переходов состояний                                    #
# ==================================================================== #

# Каждый переход описывает:
#   required_status  — статус, в котором должна быть аренда
#   next_status      — статус, в который переходим
#   timestamp_field  — поле, фиксирующее момент перехода
#   log_message      — шаблон для логгера
#   response_message — сообщение в теле ответа
#   response_key     — ключ временно́й метки в data-блоке ответа

TRANSITION_CONFIG = {
    "start_inspection": {
        "required_status": Statuses.BOOKED.value,
        "next_status": Statuses.INSPECTING.value,
        "timestamp_field": "inspection_started_at",
        "log_message": "Осмотр начат",
        "response_message": "Осмотр автомобиля успешно начат",
        "response_key": "inspection_started_at",
        "conflict_title": "Неверный статус для начала осмотра",
    },
    "start_rental": {
        "required_status": Statuses.INSPECTING.value,
        "next_status": Statuses.ACTIVE.value,
        "timestamp_field": "start_time",
        "log_message": "Аренда начата",
        "response_message": "Аренда автомобиля успешно началась",
        "response_key": "started_at",
        "conflict_title": "Неверный статус для начала аренды",
    },
    "end_rental": {
        "required_status": Statuses.ACTIVE.value,
        "next_status": Statuses.COMPLETED.value,
        "timestamp_field": "end_time",
        "log_message": "Аренда завершена",
        "response_message": "Аренда автомобиля успешно завершена",
        "response_key": "ended_at",
        "conflict_title": "Неверный статус для окончания аренды",
        'extra_fields':     {'started_at': 'start_time'}, # Единственный тип ответа в котором возвращается как время начала аренды, так и время окончания
    },
}