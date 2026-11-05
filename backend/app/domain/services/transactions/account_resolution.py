"""Which account a message names, decided by the code and not by the model (domain rules, § 1).

The model gives the mention, the type of account with the words that say it, and the currency,
each only if the message says it. What words say a type is for the model to decide: the code
has no list of them. A wrong account breaks a computed balance, so the choice follows a fixed
rule: exactly one candidate, or none.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.entities.account import Account, AccountType
from app.domain.entities.classification import Classification

_WORD = re.compile(r"[a-z0-9]+")
# A name of more words than this can be named by its initials, as "MP" for Mercado Pago.
_SINGLE_WORD = 1


@dataclass(frozen=True)
class AccountWords:
    """How the message names one account, as the model returned it: the code checks each part."""

    mention: str | None = None
    type: AccountType | None = None
    type_words: str | None = None
    currency: str | None = None


def named_account(text: str, words: AccountWords, accounts: Sequence[Account]) -> Account | None:
    """The only account the message names, or None when it names none or several."""
    candidates = account_candidates(text, words, accounts)
    return candidates[0] if len(candidates) == 1 else None


def account_candidates(
    text: str, words: AccountWords, accounts: Sequence[Account]
) -> list[Account]:
    """The accounts the message may mean: the ones to offer when there is more than one.

    The rule of the domain, step by step (domain rules, § 1).
    """
    mention = words.mention
    # 1. What the message does not write is not used: an account the model deduced, as from
    # "por transferencia", is not named.
    if is_unwritten(mention, text):
        return []
    account_type = verified_type(words.type, words.type_words, text)
    if mention is None:
        if account_type is None:
            return []
        # 4. Without a mention, the accounts of the type the message says.
        candidates = list(accounts)
    else:
        # The mention, not the rest of the message: in "con MP porque no tenía efectivo" the
        # account is the one named "MP", even though "efectivo" is the whole name of another.
        mention_words = set(_words(mention))
        # 2. Its whole name is that account, whatever the type or the currency said.
        complete = [account for account in accounts if set(_words(account.name)) <= mention_words]
        if len(complete) == 1:
            return complete
        # 3. The accounts of which the mention is a part of the name.
        candidates = [account for account in accounts if _named_by_part(account, mention_words)]
    if account_type is not None:
        # 4. Only those of the type the message says.
        candidates = [account for account in candidates if account.type is account_type]
    if words.currency is not None:
        # 5. Only those in the currency the message says.
        candidates = [account for account in candidates if account.currency == words.currency]
    return candidates


def account_words(classification: Classification, text: str) -> AccountWords:
    """How the message names the account of an expense or an income, or the one a transfer
    leaves: with the currency only if the message writes it.
    """
    return AccountWords(
        classification.account,
        classification.account_type,
        classification.account_type_words,
        verified_currency(classification, text),
    )


def verified_currency(classification: Classification, text: str) -> str | None:
    """The currency the message says: none if the words the model gave are not in it (CA-39).

    Without words, the currency counts as the model gave it: Vero decided so on 17/10/2026.
    """
    if is_unwritten(classification.currency_words, text):
        return None
    return classification.currency


def verified_type(
    account_type: AccountType | None, type_words: str | None, text: str
) -> AccountType | None:
    """The type of account the message says: none without words that say it, or with words the
    message does not write (domain rules, § 1).
    """
    if account_type is None or type_words is None or not _written_in(type_words, text):
        return None
    return account_type


def is_written(words: str, text: str) -> bool:
    """Whether those words appear in the message, whole and in the same order."""
    return _written_in(words, text)


def is_unwritten(words: str | None, text: str) -> bool:
    """Whether the model returned words the message does not write: they are never used, and
    the call counts as one whose output the validation rejected (CA-47).
    """
    return words is not None and not _written_in(words, text)


def _named_by_part(account: Account, mention_words: set[str]) -> bool:
    """Every word of the mention is in its name, or the mention is its initials."""
    name_words = _words(account.name)
    initials = "".join(word[0] for word in name_words)
    return bool(mention_words) and (
        mention_words <= set(name_words)
        or (len(name_words) > _SINGLE_WORD and mention_words == {initials})
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
