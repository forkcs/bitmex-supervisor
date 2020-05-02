class AuthenticationError(Exception):
    pass


class MarketClosedError(Exception):
    pass


class MarketEmptyError(Exception):
    pass


class MaxRetriesReachedError(Exception):
    pass


class InsufficientBalanceError(Exception):
    pass


class DuplicateClordid(Exception):
    pass
