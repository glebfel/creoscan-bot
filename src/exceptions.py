class EmptyResultsException(Exception):
    pass


class UnrecognizedException(Exception):
    pass


class WrongInputException(Exception):
    pass


class ThirdPartyApiException(Exception):
    pass


class AccountNotExist(ThirdPartyApiException):
    pass


class AccountIsPrivate(ThirdPartyApiException):
    pass


class ThirdPartyTimeoutError(ThirdPartyApiException):
    pass


class MediaNotFoundError(ThirdPartyApiException):
    pass
