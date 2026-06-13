from ....shared.kernel.log import logger

def get_tables_columns(table_exprs) -> dict:
    tables = {}
    for table in table_exprs:
        try:
            tables[table.get_name()] = table.columns
        except Exception as e:
            logger.warn(str(e))
        continue
    return tables