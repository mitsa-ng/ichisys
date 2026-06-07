import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pool import Pool
    from app.models.prize_grade import PrizeGrade


def build_ticket_plan(pool: "Pool", prize_grades: list["PrizeGrade"], total_tickets: int) -> list[dict]:
    ticket_pool: list[dict] = []

    for grade in prize_grades:
        grade.remaining_stock = 0
        for item in grade.prize_items:
            item.remaining_stock = 0
            for _ in range(item.stock):
                ticket_pool.append({
                    "pool_id": pool.id,
                    "prize_grade_id": grade.id,
                    "prize_item_id": item.id,
                    "serial_number": 0,
                    "is_drawn": False,
                })

    random.shuffle(ticket_pool)

    ticket_plan = ticket_pool[:total_tickets]

    for ticket in ticket_plan:
        gid = ticket["prize_grade_id"]
        iid = ticket["prize_item_id"]
        for grade in prize_grades:
            if grade.id == gid:
                grade.remaining_stock += 1
                if iid:
                    for item in grade.prize_items:
                        if item.id == iid:
                            item.remaining_stock += 1
                            break
                break

    extra = total_tickets - len(ticket_pool)
    if extra > 0 and prize_grades:
        for _ in range(extra):
            ticket_plan.append({
                "pool_id": pool.id,
                "prize_grade_id": random.choice(prize_grades).id,
                "prize_item_id": None,
                "serial_number": 0,
                "is_drawn": False,
            })

    random.shuffle(ticket_plan)

    for idx, ticket in enumerate(ticket_plan):
        ticket["serial_number"] = idx + 1

    return ticket_plan
