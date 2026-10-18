"""Which account a message names, decided by the code and not by the model (domain rules, § 1).

The model gives the mention, the words the message uses for the account, and the currency
only if the message says it. A wrong account breaks a computed balance, so the choice follows a
fixed rule: exactly one candidate, or none.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from app.domain.entities.account import Account, AccountType

# The words that name an account by its type, and those that only join the words of a
# mention, such as "el" in "el banco". Without accents, in lower case.
ACCOUNT_TYPE_WORDS: dict[AccountType, frozenset[str]] = {
    AccountType.BANK_ACCOUNT: frozenset({"banco"}),
    AccountType.DIGITAL_WALLET: frozenset({"billetera", "virtual"}),
    AccountType.CASH: frozenset({"efectivo", "cash"}),
}
MENTION_FILLER_WORDS = frozenset({"el", "la", "los", "las", "mi", "mis", "de", "del", "con", "en"})

_WORD = re.compile(r"[a-z0-9]+")
# A name of more words than this can be named by its initials, as "MP" for Mercado Pago.
_SINGLE_WORD = 1


def named_account(
    text: str, mention: str | None, currency: str | None, accounts: Sequence[Account]
) -> Account | None:
    """The only account the message names, or None when it names none or several."""
    candidates = account_candidates(text, mention, currency, accounts)
    return candidates[0] if len(candidates) == 1 else None


def account_candidates(
    text: str, mention: str | None, currency: str | None, accounts: Sequence[Account]
) -> list[Account]:
    """The accounts the mention may be: the ones to offer when there is more than one."""
    if mention is None or not _written_in(mention, text):
        # An account the model deduced, as from "por transferencia", is not named.
        return []
    # The mention, not the rest of the message: in "con MP porque no tenía efectivo" the account
    # is the one named "MP", even though "efectivo" is the whole name of another.
    written_words = set(_words(mention))
    complete = [account for account in accounts if set(_words(account.name)) <= written_words]
    if len(complete) == 1:
        candidates = complete
    else:
        mention_words = written_words - MENTION_FILLER_WORDS
        candidates = [account for account in accounts if _named_by_part(account, mention_words)]
    if currency is not None:
        candidates = [account for account in candidates if account.currency == currency]
    return candidates


def is_written(words: str, text: str) -> bool:
    """Whether those words appear in the message, whole and in the same order."""
    return _written_in(words, text)


def _named_by_part(account: Account, mention_words: set[str]) -> bool:
    """A word of its name, its initials, or a word of its type."""
    name_words = _words(account.name)
    initials = "".join(word[0] for word in name_words)
    return bool(
        mention_words & set(name_words)
        or (len(name_words) > _SINGLE_WORD and initials in mention_words)
        or mention_words & ACCOUNT_TYPE_WORDS.get(account.type, frozenset())
    )


def _written_in(mention: str, text: str) -> bool:
    """Whether the mention appears in the message as whole words, in the same order."""
    written = " ".join(_words(mention))
    return bool(written) and f" {written} " in f" {' '.join(_words(text))} "


def _words(text: str) -> list[str]:
    """In lower case and without accents, so "Galicia" and "galicía" are the same word."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(character for character in decomposed if not unicodedata.combining(character))
    return _WORD.findall(plain)
