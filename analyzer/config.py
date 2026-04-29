import os
from dataclasses import dataclass

@dataclass
class Config:
    goldmane_host: str = ""
    goldmane_port: int = 7443
    ca_cert: str = "certs/goldmane-ca.crt"
    client_cert: str = "certs/goldmane.crt"
    client_key: str = "certs/goldmane.key"
    demo_mode: bool = False
    lookback_seconds: int = -3600

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            goldmane_host=os.getenv("GOLDMANE_HOST", ""),
            goldmane_port=int(os.getenv("GOLDMANE_PORT", "7443")),
            ca_cert=os.getenv("GOLDMANE_CA_CERT", "certs/goldmane-ca.crt"),
            client_cert=os.getenv("GOLDMANE_CLIENT_CERT", "certs/goldmane.crt"),
            client_key=os.getenv("GOLDMANE_CLIENT_KEY", "certs/goldmane.key"),
            demo_mode=os.getenv("DEMO_MODE", "false").lower() == "true",
            lookback_seconds=int(os.getenv("LOOKBACK_SECONDS", "-3600")),
        )

    def certs_exist(self) -> bool:
        return all(os.path.exists(p) for p in [self.ca_cert, self.client_cert, self.client_key])
