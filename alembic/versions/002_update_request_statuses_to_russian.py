"""Update request statuses to Russian

Revision ID: 002
Revises: 2025_07_16_0037-41b7968bb5eb_add_foreign_key_constraints
Create Date: 2025-07-18 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002"
down_revision = "2025_07_16_0037-41b7968bb5eb_add_foreign_key_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Обновляем существующие статусы с английского на русский
    connection = op.get_bind()

    # Маппинг английских статусов на русские
    status_mapping = {
        "new": "Новая",
        "pending": "Ожидает",
        "in_progress": "В работе",
        "done": "Готово",
        "completed": "Готово",
        "cancelled": "Отказ",
    }

    # Обновляем каждый статус
    for old_status, new_status in status_mapping.items():
        connection.execute(
            sa.text(
                "UPDATE requests SET status = :new_status WHERE status = :old_status"
            ),
            {"new_status": new_status, "old_status": old_status},
        )


def downgrade() -> None:
    # Возвращаем английские статусы
    connection = op.get_bind()

    # Обратный маппинг русских статусов на английские
    status_mapping = {
        "Новая": "new",
        "Ожидает": "pending",
        "В работе": "in_progress",
        "Готово": "done",
        "Отказ": "cancelled",
        "Ожидает принятия": "pending",
        "Принял": "in_progress",
        "В пути": "in_progress",
        "Модерн": "pending",
        "НеЗаказ": "cancelled",
        "Перезвонить": "pending",
        "ТНО": "pending",
    }

    # Возвращаем каждый статус
    for old_status, new_status in status_mapping.items():
        connection.execute(
            sa.text(
                "UPDATE requests SET status = :new_status WHERE status = :old_status"
            ),
            {"new_status": new_status, "old_status": old_status},
        )
