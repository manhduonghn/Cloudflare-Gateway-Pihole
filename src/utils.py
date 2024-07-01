def chunk_list(_list: list[str], n: int):
    for i in range(0, len(_list), n):
        yield _list[i : i + n]
