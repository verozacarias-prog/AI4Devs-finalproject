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
# The order in which accounts are offered, within each currency: so it never changes.
_OFFER_ORDER = (
    AccountType.BANK_ACCOUNT,
    AccountType.DIGITAL_WALLET,
    AccountType.CASH,
    AccountType.BROKER,
    AccountType.CREDIT_CARD,
    AccountType.RECEIVABLE,
)
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
    # 1. What the message does not write is not used: an account the model deduced, as from
    # "por transferencia", is not named. A full name counts as the words that name it.
    mention = written_mention(words.mention, text, accounts)
    if words.mention is not None and mention is None:
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
        named = _named_by(mention, accounts)
        if named.complete:
            return named.accounts
        candidates = named.accounts
    if account_type is not None:
        # 4. Only those of the type the message says.
        candidates = [account for account in candidates if account.type is account_type]
    if words.currency is not None:
        # 5. Only those in the currency the message says.
        candidates = [account for account in candidates if account.currency == words.currency]
    return candidates


def named_or_mentioned(
    text: str, words: AccountWords, accounts: Sequence[Account]
) -> tuple[str | None, str | None, AccountType | None]:
    """The account the message names, or the mention and the type that named several of them,
    to offer only those.
    """
    candidates = account_candidates(text, words, accounts)
    if len(candidates) == 1:
        return candidates[0].name, None, None
    if len(candidates) > 1:
        mention = written_mention(words.mention, text, accounts)
        return None, mention, verified_type(words.type, words.type_words, text)
    return None, None, None


def chosen_account(
    text: str, said: AccountWords, accounts: Sequence[Account], offered: Sequence[Account]
) -> Account | None:
    """The account a reply chooses: by its name, or by its currency among those offered."""
    currency = said.currency
    named = account_candidates(text, said, accounts)
    if len(named) == 1:
        return named[0]
    offered_ids = {account.id for account in offered}
    among_offered = [account for account in named if account.id in offered_ids]
    if len(among_offered) == 1:
        return among_offered[0]
    if currency is not None:
        in_currency = [account for account in offered if account.currency == currency]
        if len(in_currency) == 1:
            return in_currency[0]
    return None


def offered_accounts(
    mention: str | None, account_type: AccountType | None, accounts: Sequence[Account]
) -> list[Account]:
    """The accounts the mention and the type said name, when they are more than one; or else
    all of them (CA-20).
    """
    named = list(accounts)
    if mention is not None:
        named = account_candidates(mention, AccountWords(mention), named)
    if account_type is not None:
        named = [account for account in named if account.type is account_type]
    return named if len(named) > 1 else list(accounts)


def in_offer_order(accounts: Sequence[Account], primary_currency: str) -> tuple[Account, ...]:
    """First those in the primary currency of the user, and within each currency the bank, the
    wallet and the cash before the rest, by name, so the order never changes.
    """
    return tuple(
        sorted(
            accounts,
            key=lambda account: (
                account.currency != primary_currency,
                _OFFER_ORDER.index(account.type),
                account.name,
            ),
        )
    )


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


@dataclass(frozen=True)
class _Named:
    """The accounts a mention names, and whether it names one by its whole name."""

    accounts: list[Account]
    complete: bool


def _named_by(mention: str, accounts: Sequence[Account]) -> _Named:
    """Steps 2 and 3 of the rule: the account whose whole name the mention has, if only one;
    or else the accounts of which the mention is a part of the name, or the initials.
    """
    mention_words = set(_words(mention))
    complete = [account for account in accounts if set(_words(account.name)) <= mention_words]
    if len(complete) == 1:
        return _Named(complete, complete=True)
    return _Named(
        [account for account in accounts if _named_by_part(account, mention_words)],
        complete=False,
    )


def written_mention(mention: str | None, text: str, accounts: Sequence[Account]) -> str | None:
    """The words of the message that name the account the model mentions, or None.

    A mention the message writes is itself. The full name of an account the message does not
    write counts as the words of the message that name that account and no other, by steps 2
    and 3: as if the model had copied them (domain rules, § 1; FEAT-007, CA-21).
    """
    if mention is None or _written_in(mention, text):
        return mention
    name_words = _words(mention)
    full = [account for account in accounts if _words(account.name) == name_words]
    if len(full) != 1:
        return None
    text_words = _words(text)
    for size in range(len(name_words), 0, -1):
        for start in range(len(text_words) - size + 1):
            words = " ".join(text_words[start : start + size])
            if _named_by(words, accounts).accounts == full:
                return words
    return None


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
