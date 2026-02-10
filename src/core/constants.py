NAME_LEN = 255
SHORT_STR_LEN = 64
MEDIUM_STR_LEN = 128

WEBHOOK_DEFAULT_RETRY_COUNT = 3
WEBHOOK_DEFAULT_TIMEOUT = 10

AGGREGATION_DEFAULT_ATTEMPTS = 0


# ===== Batch API field aliases (RU) =====

BATCH_IS_CLOSED = "СтатусЗакрытия"
BATCH_TASK_DESCRIPTION = "ПредставлениеЗаданияНаСмену"

BATCH_WORK_CENTER_NAME = "РабочийЦентр"
BATCH_SHIFT = "Смена"
BATCH_TEAM = "Бригада"

BATCH_NUMBER = "НомерПартии"
BATCH_DATE = "ДатаПартии"

BATCH_NOMENCLATURE = "Номенклатура"
BATCH_EKN_CODE = "КодЕКН"

BATCH_WORK_CENTER_IDENTIFIER = "ИдентификаторРЦ"

BATCH_SHIFT_START = "ДатаВремяНачалаСмены"
BATCH_SHIFT_END = "ДатаВремяОкончанияСмены"

# Pagination

DEFAULT_OFFSET = 0
DEFAULT_LIMIT = 20
MIN_LIMIT = 1
MAX_LIMIT = 100