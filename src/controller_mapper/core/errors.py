"""カスタム例外クラス群."""


class ControllerMapperError(Exception):
    """アプリ全体の基底例外."""


class DeviceNotFoundError(ControllerMapperError):
    """指定デバイスが見つからない."""


class ProfileLoadError(ControllerMapperError):
    """プロファイル読み込み失敗."""


class ProfileValidationError(ControllerMapperError):
    """プロファイル内容が不正."""


class OutputBackendError(ControllerMapperError):
    """出力バックエンドの初期化・書き込み失敗."""


class InputBackendError(ControllerMapperError):
    """入力バックエンドの初期化・読み取り失敗."""
