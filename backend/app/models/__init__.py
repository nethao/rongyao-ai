"""
数据库模型
"""
from app.models.user import User
from app.models.submission import Submission, SubmissionImage
from app.models.submission_attachment import SubmissionAttachment
from app.models.draft import Draft, DraftVersion
from app.models.wordpress_site import WordPressSite
from app.models.system_config import SystemConfig
from app.models.task_log import TaskLog
from app.models.editor_name_mapping import EditorNameMapping
from app.models.copy_editor_site_mapping import CopyEditorSiteMapping
from app.models.duplicate_log import DuplicateLog

__all__ = [
    "User",
    "Submission",
    "SubmissionImage",
    "SubmissionAttachment",
    "Draft",
    "DraftVersion",
    "WordPressSite",
    "SystemConfig",
    "TaskLog",
    "EditorNameMapping",
    "CopyEditorSiteMapping",
    "DuplicateLog",
]
