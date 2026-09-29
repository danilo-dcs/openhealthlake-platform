from typing import List, Literal, Union
import copy

from shared.models.env import EnvSettings

Operator = Literal[">","<","=","!=",">=","<=", "%"]

Direction = Literal["ASC", "DESC"]

Any = Union[str, int, list, tuple, dict]

class CouchbaseQueryBuilder:
    """ Query Order
        query_builder,
        .select(["name", "age", "school"])
        .where("name", "=" ,"danili")
        .where("age", ">", 34)
        .where("school", "!=", "university")
        .order_by_field("age", "DESC")
        .limit_to(10)
    """
    def __init__(self, scope:str, collection:str):
        settings = EnvSettings()

        self.bucket = settings.COUCHBASE_BUCKET

        self.scope = scope
        self.collection = collection

        self.select_fields = "*"
        self.filters: List[str] = []
        self.limit: Union[int, None] = None
        self.offset_value: Union[int, None] = None
        self.order_by: Union[str, None] = None
    

    def select(self, fields: Union[List[str], str] = "*", count: bool = False):
        """
        Specify the fields to be selected in the query.
        Default is all fields ('*').
        """
        if count:
            self.select_fields = "COUNT(*) AS count"
            return self
        
        if isinstance(fields, list):
            self.select_fields = ", ".join(fields)
        else:
            self.select_fields = fields
        return self

    def where(self, field: str, op: Operator, value: Any):
        """
        Add filtering conditions to the query.
        """
        if isinstance(value, str):
            self.filters.append(f"{field} {op} '{value}'")
        else:
            self.filters.append(f"{field} {op} {value}")
        return self
    
    def ilike(self, field: str, value:str):
        """
        Add filtering conditions to the query.
        """
        if isinstance(value, str):
            self.filters.append(f"LOWER({field}) LIKE '%{value.lower()}%'")
        else:
            self.filters.append(f"LOWER({field}) LIKE '%'")
        return self
    
    def where_any(self, target: str, in_filed: str, op: Operator, value: Any, satisfies=None):
        """
        Add filtering conditions to the query.
        """
        if not satisfies:
            satisfies = target

        if isinstance(value, str):
            self.filters.append(f"ANY {target} IN {in_filed} SATISFIES {satisfies} {op} '{value}' END")
        else:
            self.filters.append(f"ANY {target} IN {in_filed} SATISFIES {satisfies} {op} {value} END")
        return self
    
    def where_in(self, target: str, in_values: list[Any]):
        """
        Add filtering conditions to the query.
        """
        self.filters.append(f"{target} IN {in_values}")

        return self
    
    def where_intersect(self, target: str, in_values: list[Any]):
        """
        Add filtering conditions to the query.
        """
        self.filters.append(f"ARRAY_LENGTH(ARRAY_INTERSECT({target}, {in_values})) > 0;")

        return self

    def limit_to(self, limit: int):
        """
        Set a limit on the number of results returned.
        """
        self.limit = limit
        return self
    
    def offset(self, skip: int):
        """
        Set an offset number.
        """
        self.offset_value = skip
        return self

    def order_by_field(self, field: str, direction: Direction = "ASC"):
        """
        Add ordering to the query.
        """
        self.order_by = f"ORDER BY `{field}` {direction.upper()}"
        return self

    def build(self):
        """
        Build and return the final N1QL query.
        """
        query = f"SELECT {self.select_fields} FROM `{self.bucket}`.`{self.scope}`.`{self.collection}`"
        
        if self.filters:
            query += " WHERE " + " AND ".join(self.filters)
        
        if self.order_by:
            query += f" {self.order_by}"
        
        if self.limit:
            query += f" LIMIT {self.limit}"

        if self.offset_value:
            query += f" {self.offset_value}"
        
        return query
    
    def instance_copy(self, deep=False):
        """Return a copy of this instance."""
        return copy.deepcopy(self) if deep else copy.copy(self)