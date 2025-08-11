from dataclasses import dataclass

@dataclass
class Peer:
	user_id: str
	display_name: str
	ip: str
	port: int
	avatar_data: bytes | None = None
	avatar_type: str | None = None