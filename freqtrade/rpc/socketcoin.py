import logging
from freqtrade.rpc.rpc import RPC, RPCException, RPCHandler
from typing import Any, Dict
from fastapi_socketio import SocketManager
from fastapi import Depends, FastAPI


logger = logging.getLogger(__name__)


class SocketioFreqtradeServer(RPCHandler):
    __instance = None
    __initialized = False

    _rpc: RPC
    # Backtesting type: Backtesting
    _bt = None
    _bt_data = None
    _bt_timerange = None
    _bt_last_config: Dict[str, Any] = {}
    _has_rpc: bool = False
    _bgtask_running: bool = False
    _config: Dict[str, Any] = {}
    # Exchange - only available in webserver mode.
    _exchange = None

    def __new__(cls, *args, **kwargs):
        """
        This class is a singleton.
        We'll only have one instance of it around.
        """
        if SocketioFreqtradeServer.__instance is None:
            SocketioFreqtradeServer.__instance = object.__new__(cls)
            SocketioFreqtradeServer.__initialized = False
        return SocketioFreqtradeServer.__instance

    def __init__(self, config: Dict[str, Any], app: Any, standalone: bool = False) -> None:
        self.sio = None
        self._standalone = None
        self.app = app

        SocketioFreqtradeServer._config = config
        if self.__initialized and (standalone or self._standalone):
            return
        self._standalone: bool = standalone
        self._server = None
        SocketioFreqtradeServer.__initialized = True

        api_config = self._config['api_server']

        self.configure_app(self.app, self._config)

        self.start_api()

    def configure_app(self, app: FastAPI, config):
        self.sio = SocketManager(app=app)

        app.add_exception_handler(RPCException, self.handle_rpc_exception)

    def cleanup(self) -> None:
        """ Cleanup pending module resources """
        SocketioFreqtradeServer._has_rpc = False
        del SocketioFreqtradeServer._rpc
        if self._server and not self._standalone:
            logger.info("Stopping API Server")
            self._server.cleanup()
