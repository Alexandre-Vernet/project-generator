from dataclasses import dataclass


@dataclass
class Ports:
    front_http: int
    front_https: int
    api_http: int
    api_https: int
    db_http: int
    db_https: int
