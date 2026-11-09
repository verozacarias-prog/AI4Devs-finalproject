"""A transfer between accounts of the user, in AnswerMessage: registered, asked, continued
or discarded (FEAT-006).
"""

from __future__ import annotations

import uuid
from dataclasses import replace

from app import messages
from app.domain.entities.classification import (
    Classification,
    PendingReply,
)
from app.domain.entities.outbound_message import ResponseKind
from app.domain.entities.pending_transaction import (
    BatchStatus,
    PendingBatch,
    PendingIntent,
    PendingStatus,
    PendingTransaction,
)
from app.domain.entities.transaction import TransactionSource
from app.domain.entities.transfer import Transfer
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.transactions.pending_question import (
    transfer_question_text,
)
from app.domain.services.transactions.registration_confirmation import (
    transfer_before_opening_text,
    transfer_confirmation_text,
)
from app.domain.services.transactions.transfer_resolution import (
    AnotherCurrencyThanItsAccounts,
    DifferentCurrencies,
    MissingTransfer,
    ResolvedTransfer,
    TransferBeforeOpening,
    TransferField,
    TransferInterpretation,
    TransferResolution,
    continue_transfer,
    registered,
    resolve_transfer,
    transfer_corrections,
    transfer_from_parsed_data,
    transfer_to_parsed_data,
)
from app.domain.use_cases.messages.reply_context import (
    ReplyContext,
    add_reply,
    ask_in_pending,
    close_pending,
    closed_batch,
    fixed_text,
    new_pending,
    reject,
)


def continue_pending_transfer(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    awaiting: tuple[PendingBatch, PendingTransaction],
    classification: Classification,
) -> bool:
    """A message while a pending transfer awaits its reply (domain rules, § 5). True if it
    completed or discarded it: it uses the quota of registration (§ 12).
    """
    batch, pending = awaiting
    match classification.pending_reply:
        case PendingReply.DISCARDS:
            close_pending(unit_of_work, awaiting, PendingStatus.REJECTED, context.user.id)
            add_reply(unit_of_work, context, messages.PENDING_DISCARDED, ResponseKind.FIXED_TEXT)
            return True
        case PendingReply.CONTINUES:
            transfer, corrected = continued_transfer(context, pending, classification)
            return settle_transfer(unit_of_work, context, transfer, (batch, corrected))
        case PendingReply.OTHER_MOVEMENT | None:
            # Not about the pending: it keeps waiting, and the message gets its fixed text.
            # Another movement joins the batch before it gets here (FEAT-007, CA-13).
            add_reply(unit_of_work, context, fixed_text(classification), ResponseKind.FIXED_TEXT)
            return False


def continued_transfer(
    context: ReplyContext, pending: PendingTransaction, classification: Classification
) -> tuple[TransferInterpretation, PendingTransaction]:
    """What a reply makes of a pending transfer, and the pending with the corrections counted."""
    previous = transfer_from_parsed_data(pending.parsed_data, context.today)
    transfer = continue_transfer(previous, classification, context.message.text, context.accounts)
    corrected = replace(
        pending,
        corrected_fields_count=pending.corrected_fields_count
        + transfer_corrections(previous, transfer),
    )
    return transfer, corrected


def settle_transfer(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    interpretation: TransferInterpretation,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> bool:
    """Registers it, says why not, or asks what is missing, in a new pending or in the open one
    (FEAT-006). False when it cannot be registered yet, because it needs a rate (CA-14).
    """
    resolution = resolve_user_transfer(context, interpretation)
    match resolution:
        case ResolvedTransfer():
            _register_transfer(unit_of_work, context, resolution, interpretation, awaiting)
        case TransferBeforeOpening():
            text = transfer_before_opening_text(resolution.account.name, resolution.opened_on)
            reject(unit_of_work, context, awaiting, text)
        case DifferentCurrencies():
            reject(unit_of_work, context, awaiting, messages.TRANSFER_IN_DIFFERENT_CURRENCIES)
        case AnotherCurrencyThanItsAccounts():
            reject(unit_of_work, context, awaiting, messages.TRANSFER_IN_ANOTHER_CURRENCY)
        case MissingTransfer():
            ask_in_pending(
                unit_of_work,
                context,
                transfer_question_text(resolution),
                transfer_to_parsed_data(resolution.interpretation),
                tuple(field.value for field in resolution.fields),
                PendingIntent.TRANSFER,
                awaiting,
            )
    return not isinstance(resolution, (DifferentCurrencies, AnotherCurrencyThanItsAccounts))


def resolve_user_transfer(
    context: ReplyContext, interpretation: TransferInterpretation
) -> TransferResolution:
    return resolve_transfer(
        interpretation, context.accounts, context.user.time_zone, context.user.primary_currency
    )


def transfer_missing_of(context: ReplyContext, pending: PendingTransaction) -> MissingTransfer:
    """What an open pending transfer lacks, as it was asked: from what it kept, the same way."""
    interpretation = transfer_from_parsed_data(pending.parsed_data, context.today)
    resolution = resolve_user_transfer(context, interpretation)
    if not isinstance(resolution, MissingTransfer):
        # Something changed since it was asked, as an account that was renamed: the question
        # is the one its missing fields say, offering every account.
        resolution = MissingTransfer(
            interpretation=interpretation,
            fields=tuple(TransferField(field) for field in pending.missing_fields),
            from_account=None,
            to_account=None,
            from_options=tuple(context.accounts),
            to_options=tuple(context.accounts),
        )
    return resolution


def transfer_currency(context: ReplyContext, missing: MissingTransfer) -> str:
    """The currency its amount is in: the one of an account it names, or else the one the
    messages say, or else the primary (C2-15). With an account, the one said is the same:
    another one gets the fixed text of CA-14.
    """
    account = missing.from_account or missing.to_account
    if account is not None:
        return account.currency
    return missing.interpretation.currency or context.user.primary_currency


def _register_transfer(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    resolved: ResolvedTransfer,
    interpretation: TransferInterpretation,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> None:
    """The transfer and its confirmation. Its pending is promoted and its batch closed, the open
    one or a new batch of one (§ 5).
    """
    user_id = context.user.id
    transfer = new_transfer(context, resolved)
    unit_of_work.transfers.add(transfer)
    confirmation = add_reply(
        unit_of_work, context, transfer_confirmation(resolved, None), ResponseKind.REGISTRATION
    )
    parsed = transfer_to_parsed_data(registered(interpretation, resolved))
    if awaiting is not None:
        batch, pending = awaiting
        unit_of_work.pendings.update(
            replace(
                pending,
                parsed_data=parsed,
                missing_fields=(),
                resulting_transfer_id=transfer.id,
                status=PendingStatus.PROMOTED,
                resolved_by=user_id,
            )
        )
        unit_of_work.pendings.update_batch(
            replace(
                batch,
                awaiting_reply=False,
                confirmation_message_id=confirmation.id,
                status=BatchStatus.CLOSED,
            )
        )
        return
    batch = closed_batch(context, confirmation)
    unit_of_work.pendings.add_batch(batch)
    unit_of_work.pendings.add(
        replace(
            new_pending(context, batch, parsed, (), PendingStatus.PROMOTED, None, user_id),
            intent=PendingIntent.TRANSFER,
            resulting_transfer_id=transfer.id,
        )
    )


def new_transfer(context: ReplyContext, resolved: ResolvedTransfer) -> Transfer:
    return Transfer(
        id=uuid.uuid4(),
        user_id=context.user.id,
        from_account_id=resolved.from_account.id,
        from_amount=resolved.amount,
        from_currency=resolved.from_account.currency,
        to_account_id=resolved.to_account.id,
        to_amount=resolved.amount,
        to_currency=resolved.to_account.currency,
        # Both sides in the same currency: there is no rate (§ 13).
        exchange_rate=None,
        transfer_date=resolved.transfer_date,
        source=TransactionSource.MANUAL,
    )


def transfer_confirmation(resolved: ResolvedTransfer, position: int | None) -> str:
    """What its confirmation says of it: alone, or with its number in a batch of several."""
    return transfer_confirmation_text(
        amount=resolved.amount,
        currency=resolved.from_account.currency,
        from_account_name=resolved.from_account.name,
        to_account_name=resolved.to_account.name,
        transfer_date=resolved.transfer_date,
        position=position,
    )
