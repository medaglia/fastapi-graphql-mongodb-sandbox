from typing import Any, Callable, Optional

import strawberry
from beanie.odm.enums import SortDirection
from strawberry.extensions import FieldExtension
from strawberry.field import StrawberryField
from strawberry.types import Info


@strawberry.type
class PageMeta:
    next_cursor: Optional[str] = strawberry.field(
        description="The next cursor to continue with."
    )


class PaginatedResult:
    pass


class CursorPagination:
    limit: int = 10
    cursor: Optional[str] = None
    results: list[PaginatedResult]
    next_cursor: Optional[str] = None

    def __init__(self, limit: int = 10, cursor: Optional[str] = None):
        self.limit = limit
        self.cursor = cursor

    async def paginate(
        self, qry, cursor_key, sort_direction: SortDirection = SortDirection.ASCENDING
    ):
        self.next_cursor = None

        if self.cursor:
            qry = qry.find(cursor_key >= self.cursor)

        qry = qry.sort(cursor_key).limit(self.limit + 1)
        self.results = await qry.to_list()

        if len(self.results) > self.limit:
            self.next_cursor = self.results[-1].external_id
            self.results.pop()
