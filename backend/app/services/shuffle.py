import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pool import Pool
    from app.models.prize_grade import PrizeGrade


def build_ticket_plan(pool: "Pool", prize_grades: list["PrizeGrade"]) -> list[dict]:
    """
    Build a flat list of ticket payloads based on prize grade remaining_stock,
    then shuffle them randomly (Fisher-Yates).
    Each ticket maps to a serial_number and a prize_grade_id.
    """
    ticket_plan: list[dict] = []

    for grade in prize_grades:
        for _ in range(grade.remaining_stock):
            ticket_plan.append({
                "pool_id": pool.id,
                "prize_grade_id": grade.id,
                "serial_number": 0,
                "is_drawn": False,
            })

    random.shuffle(ticket_plan)

    for idx, ticket in enumerate(ticket_plan):
        ticket["serial_number"] = idx + 1

    return ticket_plan
