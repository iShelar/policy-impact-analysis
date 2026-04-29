import grpc
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "grpc_libs"))
import api_pb2
import api_pb2_grpc

from analyzer.config import Config


class GoldmaneConnectionError(Exception):
    pass


class GoldmaneClient:
    def __init__(self, config: Config):
        self.config = config
        self._channel = None
        self._flows_stub = None
        self._stats_stub = None
        self._connect()

    def _connect(self):
        cfg = self.config
        try:
            with open(cfg.ca_cert, "rb") as f:
                root_certs = f.read()
            with open(cfg.client_cert, "rb") as f:
                cert_chain = f.read()
            with open(cfg.client_key, "rb") as f:
                private_key = f.read()
        except FileNotFoundError as e:
            raise GoldmaneConnectionError(f"Certificate file not found: {e}")

        creds = grpc.ssl_channel_credentials(
            root_certificates=root_certs,
            private_key=private_key,
            certificate_chain=cert_chain,
        )
        self._channel = grpc.secure_channel(
            f"{cfg.goldmane_host}:{cfg.goldmane_port}", creds
        )
        self._flows_stub = api_pb2_grpc.FlowsStub(self._channel)
        self._stats_stub = api_pb2_grpc.StatisticsStub(self._channel)

    def health_check(self, timeout: float = 3.0) -> bool:
        try:
            grpc.channel_ready_future(self._channel).result(timeout=timeout)
            return True
        except grpc.FutureTimeoutError:
            return False

    def get_staged_policy_stats(self, time_series: bool = True) -> list[dict]:
        """
        Query per-staged-policy packet allow/deny statistics.
        Returns a list of dicts with keys:
          name, namespace, kind, allowed_in, denied_in, allowed_out, denied_out, timestamps
        """
        request = api_pb2.StatisticsRequest(
            start_time_gte=self.config.lookback_seconds,
            start_time_lt=0,
            type=api_pb2.PacketCount,
            group_by=api_pb2.Policy,
            time_series=time_series,
            policy_match=api_pb2.PolicyMatch(
                kind=api_pb2.StagedNetworkPolicy,
            ),
        )
        results = []
        try:
            for stat in self._stats_stub.List(request, timeout=10):
                results.append({
                    "name": stat.policy.name,
                    "namespace": stat.policy.namespace,
                    "tier": stat.policy.tier,
                    "kind": api_pb2.PolicyKind.Name(stat.policy.kind),
                    "allowed_in": list(stat.allowed_in),
                    "denied_in": list(stat.denied_in),
                    "allowed_out": list(stat.allowed_out),
                    "denied_out": list(stat.denied_out),
                    "timestamps": list(stat.x),
                })
        except grpc.RpcError as e:
            raise GoldmaneConnectionError(f"gRPC error: {e.code()}: {e.details()}")
        return results

    def list_recent_flows(self, page_size: int = 200) -> list[dict]:
        """
        List recent flows. Returns a list of dicts.
        """
        request = api_pb2.FlowListRequest(
            start_time_gte=self.config.lookback_seconds,
            start_time_lt=0,
            page_size=page_size,
        )
        results = []
        try:
            response = self._flows_stub.List(request, timeout=10)
            for fr in response.flows:
                flow = fr.flow
                key = flow.Key
                pending = [
                    {
                        "name": p.name,
                        "namespace": p.namespace,
                        "action": api_pb2.Action.Name(p.action),
                        "kind": api_pb2.PolicyKind.Name(p.kind),
                    }
                    for p in key.policies.pending_policies
                    if p.kind == api_pb2.StagedNetworkPolicy
                ]
                results.append({
                    "start_time": flow.start_time,
                    "source_name": key.source_name,
                    "source_namespace": key.source_namespace,
                    "source_type": api_pb2.EndpointType.Name(key.source_type),
                    "dest_name": key.dest_name,
                    "dest_namespace": key.dest_namespace,
                    "dest_type": api_pb2.EndpointType.Name(key.dest_type),
                    "dest_port": key.dest_port,
                    "proto": key.proto,
                    "action": api_pb2.Action.Name(key.action),
                    "packets_in": flow.packets_in,
                    "packets_out": flow.packets_out,
                    "bytes_in": flow.bytes_in,
                    "pending_staged_policies": pending,
                    "num_connections": flow.num_connections_started,
                })
        except grpc.RpcError as e:
            raise GoldmaneConnectionError(f"gRPC error: {e.code()}: {e.details()}")
        return results

    def close(self):
        if self._channel:
            self._channel.close()
