SAFE_ARCHIVE_RETENTION_DAYS = 30
CURRENT_LOG_RETENTION_DAYS = 7


def should_prune_archive(age_days: int) -> bool:
    return age_days > SAFE_ARCHIVE_RETENTION_DAYS
