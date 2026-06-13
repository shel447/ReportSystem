from pydantic import BaseModel


class ForeignKey(BaseModel):
    stmt: str = ""
    table: str = ""
    column: str = ""
    ref_table: str = ""
    ref_column: str = ""

    def __str__(self):
        return f"{self.table}.{self.column} = {self.ref_table}.{self.ref_column}"

    def __repr__(self):
        return self.__str__()